# -*- coding: utf-8 -*-
import logging
import json

from flask import g, request, url_for
from http import HTTPStatus
from flasgger import swag_from
from pathlib import Path

from vantage6.common.globals import STRING_ENCODING
from vantage6.server import db
from vantage6.server.permission import (
    Scope as S,
    PermissionManager,
    Operation as P
)
from vantage6.server.resource import only_for, ServicesResources
from vantage6.server.resource._schema import (
    TaskSchema,
    TaskIncludedSchema,
    TaskResultSchema
)


module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base, services):
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Task,
        path,
        endpoint='task_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
    )
    api.add_resource(
        Task,
        path + '/<int:id>',
        endpoint='task_with_id',
        methods=('GET', 'DELETE'),
        resource_class_kwargs=services
    )
    api.add_resource(
        TaskResult,
        path + '/<int:id>/result',
        endpoint='task_result',
        methods=('GET',),
        resource_class_kwargs=services
    )


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager):
    add = permissions.appender(module_name)

    add(scope=S.GLOBAL, operation=P.VIEW,
        description="view any task")
    add(scope=S.ORGANIZATION, operation=P.VIEW, assign_to_container=True,
        assign_to_node=True, description="view tasks of your organization")

    add(scope=S.GLOBAL, operation=P.EDIT, description="edit any task")
    add(scope=S.ORGANIZATION, operation=P.EDIT,
        description="edit tasks of your organization")

    add(scope=S.GLOBAL, operation=P.CREATE, description="create a new task")
    add(scope=S.ORGANIZATION, operation=P.CREATE,
        description=(
            "create a new task for collaborations in which your organization "
            "participates with"
        )
    )

    add(scope=S.GLOBAL, operation=P.DELETE,
        description="delete a task")
    add(scope=S.ORGANIZATION, operation=P.DELETE,
        description=(
            "delete a task from a collaboration in which your organization "
            "participates with"
        )
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Task(ServicesResources):
    """Resource for /api/task"""

    task_schema = TaskSchema()
    task_result_schema = TaskIncludedSchema()

    def __init__(self, socketio, mail, api, permissions):
        super().__init__(socketio, mail, api, permissions)
        self.r = getattr(self.permissions, module_name)

    @only_for(["user", "node", "container"])
    @swag_from(str(Path(r"swagger/get_task_with_id.yaml")),
               endpoint='task_with_id')
    @swag_from(str(Path(r"swagger/get_task_without_id.yaml")),
               endpoint='task_without_id')
    def get(self, id=None):
        """List tasks"""
        task = db.Task.get(id)
        if not task:
            return {"msg": f"task id={id} is not found"}, HTTPStatus.NOT_FOUND

        # determine the organization to which the auth belongs
        if g.container:
            auth_org_id = g.container["organization_id"]
        elif g.node:
            auth_org_id = g.node.organization_id
        else:  # g.user:
            auth_org_id = g.user.organization_id
        auth_org = db.Organization.get(auth_org_id)

        # obtain schema
        schema = self.task_result_schema \
            if request.args.get('include') == 'results' else self.task_schema

        # check permissions, and return result
        if id:
            if not self.r.v_glo.can():
                org_ids = [org.id for org in task.collaboration.organizations]
                if not (self.r.v_org.can() and auth_org.id in org_ids):
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED
            return schema.dump(task, many=False).data, HTTPStatus.OK
        else:
            if self.r.v_glo.can():
                return schema.dump(task, many=True).data, HTTPStatus.OK
            elif self.r.v_org.can():
                filtered = filter(
                    lambda t: auth_org in t.collaboration.organizations,
                    filter(lambda t: bool(t.collaboration), task)
                )
                return schema.dump(filtered, many=True).data, HTTPStatus.OK
            else:
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

    @only_for(["user", "container"])
    @swag_from(str(Path(r"swagger/post_task_without_id.yaml")),
               endpoint='task_without_id')
    def post(self):
        """Create a new Task."""
        # TODO https://marshmallow.readthedocs.io/en/stable/examples.html#quotes-api-flask-sqlalchemy
        data = request.get_json()
        collaboration_id = data.get('collaboration_id')
        collaboration = db.Collaboration.get(collaboration_id)

        if not collaboration:
            return {"msg": f"Collaboration id={collaboration_id} not found!"},\
                   HTTPStatus.NOT_FOUND

        organizations_json_list = data.get('organizations')
        org_ids = [org.get("id") for org in organizations_json_list]
        db_ids = collaboration.get_organization_ids()

        # Check that all organization ids are within the collaboration, this
        # also ensures us that the organizations exist
        if not set(org_ids).issubset(db_ids):
            return {"msg": (
                f"At least one of the supplied organizations in not within "
                f"the collaboration."
            )}, HTTPStatus.BAD_REQUEST

        # figure out the initiator organization of the task
        if g.user:
            initiator = g.user.organization
        else:  # g.container:
            initiator = db.Node.get(g.container["node_id"]).organization

        # Create the new task in the database
        image = data.get('image', '')

        # verify permissions
        if g.user:

            if not self.r.c_glo.can():
                c_orgs = collaboration.organizations
                if not (self.r.c_org.can() and g.user.organization in c_orgs):
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED

        elif g.container:
            # verify that the container has permissions to create the task
            if not self.__verify_container_permissions(g.container, image,
                                                       collaboration_id):
                return {"msg": "Container-token is not valid"}, \
                    HTTPStatus.UNAUTHORIZED

        # permissions ok, create record
        task = db.Task(collaboration=collaboration, name=data.get('name', ''),
                       description=data.get('description', ''), image=image,
                       initiator=initiator)

        # create run_id. Users can only create top-level -tasks (they will not
        # have sub-tasks). Therefore, always create a new run_id. Tasks created
        # by containers are always sub-tasks
        if g.user:
            task.run_id = task.next_run_id()
            task.database = data.get('database', 'default')
            log.debug(f"New run_id {task.run_id}")
        elif g.container:
            task.database = data.get('database', g.container['database'])
            task.parent_id = g.container["task_id"]
            task.run_id = db.Task.get(g.container["task_id"]).run_id
            log.debug(f"Sub task from parent_id={task.parent_id}")

        # ok commit session...
        task.save()

        # if the 'master'-flag is set to true the (master) task is executed on
        # a node in the collaboration from the organization to which the user
        # belongs. If also organization_ids are supplied, then these are
        # ignored.
        # TODO in this case the user *must* have a node attached to this
        # collaboration
        # TODO this does not make a lot of sense as the `organizations` input
        # should only contain the organization where the master container
        # shoudl run
        assign_orgs = []
        if data.get("master", False) and g.user:
            for org in organizations_json_list:
                if org['id'] == g.user.organization_id:
                    assign_orgs = [org]
                    break
            if not assign_orgs:
                return {'msg': 'You\'re trying to create a master task. '
                        'However you do not have a node yourself in this '
                        'collaboration!'}, HTTPStatus.BAD_REQUEST
        else:
            assign_orgs = organizations_json_list

        # now we need to create results for the nodes to fill. Each node
        # receives their instructions from a result, not from the task itself
        log.debug(f"Assigning task to {len(assign_orgs)} nodes.")
        for org in assign_orgs:
            organization = db.Organization.get(org['id'])
            log.debug(f"Assigning task to '{organization.name}'.")
            input_ = org.get('input')
            # FIXME: legacy input from the client, could be removed at some
            # point
            if isinstance(input_, dict):
                input_ = json.dumps(input_).encode(STRING_ENCODING)
            # Create result
            result = db.Result(
                task=task,
                organization=organization,
                input=input_,
            )
            result.save()

        # notify nodes a new task available (only to online nodes), nodes that
        # are offline will receive this task on sign in.
        self.socketio.emit('new_task', task.id, namespace='/tasks',
                           room=f'collaboration_{task.collaboration_id}')

        # add some logging
        log.info(f"New task for collaboration '{task.collaboration.name}'")
        if g.user:
            log.debug(f" created by: '{g.user.username}'")
        else:
            log.debug(f" created by container on node_id="
                      f"{g.container['node_id']}"
                      f" for (master) task_id={g.container['task_id']}")

        log.debug(f" url: '{url_for('task_with_id', id=task.id)}'")
        log.debug(f" name: '{task.name}'")
        log.debug(f" image: '{task.image}'")

        return self.task_schema.dump(task, many=False).data, HTTPStatus.CREATED

    @staticmethod
    def __verify_container_permissions(container, image, collaboration_id):
        """Validates that the container is allowed to create the task."""

        # check that the image is allowed
        # if container["image"] != task.image:
        # FIXME why?
        if not image.endswith(container["image"]):
            log.warning((f"Container from node={container['node_id']} "
                         f"attempts to post a task using illegal image!?"))
            log.warning(f"  task image: {image}")
            log.warning(f"  container image: {container['image']}")
            return False

        # check master task is not completed yet
        if db.Task.get(container["task_id"]).complete:
            log.warning(
                f"Container from node={container['node_id']} "
                f"attempts to start sub-task for a completed "
                f"task={container['task_id']}"
            )
            return False

        # check that node id is indeed part of the collaboration
        if not container["collaboration_id"] == collaboration_id:
            log.warning(
                f"Container attempts to create a task outside "
                f"collaboration_id={container['collaboration_id']} in "
                f"collaboration_id={collaboration_id}!"
            )
            return False

        return True

    @only_for(['user'])
    @swag_from(str(Path(r"swagger/delete_task_with_id.yaml")),
               endpoint='task_with_id')
    def delete(self, id):
        """Deletes a task and their results."""

        task = db.Task.get(id)
        if not task:
            return {"msg": f"task id={id} not found"}, HTTPStatus.NOT_FOUND

        # validate permissions
        if not self.r.d_glo.can():
            orgs =  task.collaboration.organizations
            if not (self.r.d_org.can() and g.user.organization in orgs):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # retrieve results that belong to this task
        log.info(f'Removing task id={task.id}')
        for result in task.results:
            log.info(f" Removing result id={result.id}")
            result.delete()

        # permissions ok, delete...
        task.delete()

        return {"msg": f"task id={id} and its result successfully deleted"}, \
            HTTPStatus.OK


class TaskResult(ServicesResources):
    """Resource for /api/task/<int:id>/result"""

    task_result_schema = TaskResultSchema()

    def __init__(self, socketio, mail, api, permissions):
        super().__init__(socketio, mail, api, permissions)
        self.r = getattr(self.permissions, "result")

    @only_for(['user', 'container'])
    @swag_from(str(Path(r"swagger/get_task_result.yaml")),
               endpoint='task_result')
    def get(self, id):
        """Return results for task."""
        task = db.Task.get(id)
        if not task:
            return {"msg": f"task id={id} not found"}, \
                HTTPStatus.NOT_FOUND

        if g.user:
            org = g.user.organization
        else:
            org = db.Organization.get(g.container['organization_id'])

        if not self.r.v_glo.can():
            c_orgs = task.collaboration.organizations
            if not (self.r.v_org.can() and org in c_orgs):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        return self.task_result_schema.dump(task.results, many=True).data, \
            HTTPStatus.OK
