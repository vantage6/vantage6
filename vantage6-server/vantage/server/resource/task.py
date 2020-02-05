# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/task'
"""
import logging
import json

from flask import g, request, url_for
from flask_restful import Resource
from . import with_user_or_node, with_user, only_for
from ._schema import TaskSchema, TaskIncludedSchema, TaskResultSchema
from http import HTTPStatus
from flasgger import swag_from
from pathlib import Path

from vantage.server import db
from vantage.server import socketio
from vantage.util import (
    prepare_bytes_for_transport, 
    unpack_bytes_from_transport
)
from vantage.constants import STRING_ENCODING

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, API_BASE):
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Task,
        path,
        endpoint='task_without_id',
        methods=('GET', 'POST')
    )
    api.add_resource(
        Task,
        path + '/<int:id>',
        endpoint='task_with_id',
        methods=('GET', 'DELETE')
    )
    api.add_resource(
        TaskResult,
        path + '/<int:id>/result',
        endpoint='task_result',
        methods=('GET',)
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Task(Resource):
    """Resource for /api/task"""

    task_schema = TaskSchema()
    task_result_schema = TaskIncludedSchema()

    @only_for(["user", "node", "container"])
    @swag_from(str(Path(r"swagger/get_task_with_id.yaml")), endpoint='task_with_id')
    @swag_from(str(Path(r"swagger/get_task_without_id.yaml")), endpoint='task_without_id')
    def get(self, id=None):
        task = db.Task.get(id)
        if not task:
            return {"msg": "task id={} is not found"}, HTTPStatus.NOT_FOUND

        s = self.task_result_schema if request.args.get('include') == 'results' else self.task_schema
        return s.dump(task, many=not id).data, HTTPStatus.OK


    @only_for(["user", "container"])
    @swag_from(str(Path(r"swagger/post_task_without_id.yaml")), endpoint='task_without_id')
    def post(self):
        """Create a new Task."""        
        if not request.is_json:
            return {"msg": "No JSON body found..."}, HTTPStatus.BAD_REQUEST

        data = request.get_json()

        collaboration_id = data.get('collaboration_id')
        collaboration = db.Collaboration.get(collaboration_id)

        if not collaboration:
            return {"msg": f"collaboration id={collaboration_id} not found"},\
            HTTPStatus.NOT_FOUND

        # check that the organization ids are within the collaboration
        organizations_json_list = data.get('organizations')
        org_ids = [org.get("id") for org in organizations_json_list]
        db_ids = collaboration.get_organization_ids()

        # TODO what happens if user's organization does not have a node that
        # is part of a the collaboration
        # if the 'master'-flag is set to true the (master) task is executed on 
        # a node in the collaboration from the organization to which the user 
        # belongs. If also organization_ids are supplied, then these are ignored.
        if data.get("master", False) and g.user:            
            org_ids = [g.user.organization_id]

        if not all([org_id in db_ids for org_id in org_ids]):
            return {"msg": ( 
                f"At least one of the supplied organizations in not within "
                f"the collaboration"
            )}, HTTPStatus.BAD_REQUEST
        
        if g.user:
            initiator = g.user.organization
        elif g.container:
            initiator = db.Node.get(g.container["node_id"]).organization
        else:
            initiator = None

        # create new task
        task = db.Task(
            collaboration=collaboration,
            name=data.get('name', ''),
            description=data.get('description', ''),
            image=data.get('image', ''),
            database=data.get('database', ''),
            initiator=initiator
        )

        if g.user:
            if not self.__verify_user_permissions(g.user, task):
                return {"msg": "You lack the permission to do that!"}, HTTPStatus.UNAUTHORIZED

            # user can only create master-tasks (it is not required to have sub-tasks)
            task.run_id = task.next_run_id()
            log.debug(f"New run_id {task.run_id}")
            
        elif g.container: 
            # verify that the container has permissions to create the task
            if not self.__verify_container_permissions(g.container, task):
                return {"msg": "Container-token is not valid"}, HTTPStatus.UNAUTHORIZED

            # container tasks are always sub-tasks
            task.parent_task_id = g.container["task_id"]
            task.run_id = db.Task.get(g.container["task_id"]).run_id
            log.debug(f"Sub task from parent_task_id={task.parent_task_id}")
        
        # permissions ok, save to DB
        task.save()
        
        organizations = [db.Organization.get(id_) for id_ in org_ids]
        log.debug(f"Assigning task to {len(organizations)} nodes.")
        for organization in organizations:
            log.debug(f"Assigning task to '{organization.name}'.")

            # get organization specific encrypted input
            # TODO make this cleaner...
            input_ = [org.get("input") for org in organizations_json_list \
                if org.get("id")==organization.id].pop()

            if isinstance(input_, dict):
                input_ = prepare_bytes_for_transport(
                    json.dumps(input_).encode(STRING_ENCODING)
                )

            result = db.Result(
                task=task, 
                organization=organization,
                input=input_,
            )
            result.save()

        # notify nodes a new task available (only to online nodes)
        socketio.emit(
            'new_task', 
            task.id, 
            room='collaboration_' + str(task.collaboration_id),
            namespace='/tasks'
        )

        log.info(f"New task created for collaboration '{task.collaboration.name}'")
        if g.type == 'user':
            log.debug(f" created by: '{g.user.username}'")
        else:
            log.debug((f" created by container on node_id={g.container['node_id']}"
                       f" for (master) task_id={g.container['task_id']}"))
        log.debug(f" url: '{url_for('task_with_id', id=task.id)}'")
        log.debug(f" name: '{task.name}'")
        log.debug(f" image: '{task.image}'")

        return self.task_schema.dump(task, many=False)

    @staticmethod
    def __verify_user_permissions(user, task: db.Task):
        """Verify that user is permitted to create task"""

        # I have the power!
        if "root" in g.user.roles:
            return True

        # user is within organization that is part of the collaboration
        return g.user.organization_id in task.collaboration.get_organization_ids()

    @staticmethod
    def __verify_container_permissions(container, task):
        """Validates that the container is allowed to create the task."""

        # check that the image is allowed
        if container["image"] != task.image:
            log.warning((f"Container from node={container['node_id']} " 
                f"attempts to post a task using illegal image={task.image}"))
            return False

        # check master task is not completed yet
        if db.Task.get(container["task_id"]).complete:
            log.warning((f"Container from node={container['node_id']} attempts "
                f"to start sub-task for a completed task={container['task_id']}"))
            return False

        # check that node id is indeed part of the collaboration
        if not container["collaboration_id"] == task.collaboration.id:
            log.warning((f"Container attempts to create a task outside "
                f"collaboration_id={container['collaboration_id']} in "
                f"collaboration_id={task.collaboration_id}!"))
            return False

        return True

    @only_for(['user'])
    @swag_from(str(Path(r"swagger/delete_task_with_id.yaml")), endpoint='task_with_id')
    def delete(self, id):
        """Deletes a task"""
        # TODO we might want to delete the corresponding results also?

        task = db.Task.get(id)
        if not task:
            return {"msg": "task id={} not found".format(id)}, HTTPStatus.NOT_FOUND

        task.delete()
        return {"msg": "task id={} successfully deleted".format(id)}, HTTPStatus.OK


class TaskResult(Resource):
    """Resource for /api/task/<int:id>/result"""

    task_result_schema = TaskResultSchema()

    @only_for(['user', 'container'])
    @swag_from(str(Path(r"swagger/get_task_result.yaml")), endpoint='task_result')
    def get(self, id):
        """Return results for task."""
        task = db.Task.get(id)
        if not task:
            return {"msg": "task id={} not found".format(id)}, HTTPStatus.NOT_FOUND

        return self.task_result_schema.dump(task.results, many=True).data, HTTPStatus.OK

