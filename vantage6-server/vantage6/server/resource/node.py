# -*- coding: utf-8 -*-
import logging
import uuid
import json

from pathlib import Path
from http import HTTPStatus
from flasgger.utils import swag_from
from flask import g, request
from flask_restful import reqparse

from vantage6.server.resource import with_user_or_node, with_user
from vantage6.server.resource import ServicesResources
from vantage6.server import db
from vantage6.server.resource._schema import (
    TaskIncludedSchema,
    TaskSchema,
    NodeSchema
)


module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base, services):
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Node,
        path,
        endpoint='node_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
    )
    api.add_resource(
        Node,
        path + '/<int:id>',
        endpoint='node_with_id',
        methods=('GET', 'DELETE', 'PATCH'),
        resource_class_kwargs=services
    )
    api.add_resource(
        NodeTasks,
        path + '/<int:id>/task',
        endpoint='node_tasks',
        methods=('GET', ),
        resource_class_kwargs=services
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Node(ServicesResources):

    # Schemas
    node_schema = NodeSchema()

    @with_user_or_node
    @swag_from(str(Path(r"swagger/get_node_with_id.yaml")),
               endpoint='node_with_id')
    @swag_from(str(Path(r"swagger/get_node_without_id.yaml")),
               endpoint='node_without_id')
    def get(self, id=None):
        results = db.Node.get(id)
        user_or_node = g.user or g.node

        # Only users can be root, not containers.
        is_root = False
        if g.user:
            is_root = g.user.username == 'root'

        if id:
            if not results:
                msg = {"msg": f"Couldn't find node {id}"}
                return msg, HTTPStatus.NOT_FOUND

            if is_root:
                # Let's not make a fuss ...
                return self.node_schema.dump(results, many=False)

            if (results.organization_id != user_or_node.organization_id):
                msg = {"msg": "you are not allowed to see this node"}
                return msg, HTTPStatus.FORBIDDEN  # 403

        else:
            if not is_root:
                # only the results of the user's organization are returned
                org_id = g.user.organization_id
                results = [n for n in results if n.organization_id == org_id]

        return self.node_schema.dump(results, many=not id).data, HTTPStatus.OK

    @with_user
    @swag_from(str(Path(r"swagger/post_node_without_node_id.yaml")),
               endpoint='node_without_id')
    def post(self):

        parser = reqparse.RequestParser()
        parser.add_argument(
            "collaboration_id",
            type=int,
            required=True,
            help="This field cannot be left blank!"
        )
        data = parser.parse_args()

        collaboration = db.Collaboration.get(data["collaboration_id"])

        # check that the collaboration exists
        if not collaboration:
            return {"msg": f"collaboration_id '{data['collaboration_id']}' "
                    "does not exist"}, HTTPStatus.NOT_FOUND  # 404

        # new api-key which node can use to authenticate
        api_key = str(uuid.uuid1())

        # store the new node
        # TODO an admin does not have to belong to an organization?
        # TODO we need to check that the organization belongs to the
        # collaboration
        is_root = g.user.username == 'root'
        if is_root:
            organization = db.Organization.get(data["organization_id"])
        else:
            organization = g.user.organization

        node = db.Node(
            name=f"{organization.name} - {collaboration.name} Node",
            collaboration=collaboration,
            organization=organization,
            api_key=api_key
        )
        node.save()

        return self.node_schema.dump(node).data, HTTPStatus.CREATED  # 201

    @with_user
    @swag_from(str(Path(r"swagger/delete_node_with_id.yaml")),
               endpoint='node_with_id')
    def delete(self, id):
        """delete node account"""
        node = db.Node.get(id)

        if not node:
            return {"msg": f"node with id={id} not found"}, \
                HTTPStatus.NOT_FOUND  # 404

        if node.organization_id != g.user.organization_id \
                and g.user.username != "root":
            return {"msg": "you are not allowed to delete this node"}, \
                HTTPStatus.FORBIDDEN  # 403

        node.delete()

        return {"msg": "successfully deleted node id={id}"}, \
            HTTPStatus.OK  # 200

    @with_user_or_node
    @swag_from(str(Path(r"swagger/patch_node_with_id.yaml")),
               endpoint='node_with_id')
    def patch(self, id):
        """update existing node"""
        node = db.Node.get(id)

        # do not create new nodes here
        if not node:
            return {"msg": "Use POST to create a new node"}, \
                HTTPStatus.FORBIDDEN  # 403

        data = request.get_json()
        if 'state' in data:
            data['state'] = json.dumps(data['state'])

        if g.node:
            if g.node.id == node.id:
                log.debug("Hey! It's me! I got this!")
                node.update(include=['status', 'state'], **data)
            else:
                log.debug("This doesn't seem right! You don't look like me!?")
                return {"msg": "you are not allowed to edit this node"}, \
                    HTTPStatus.FORBIDDEN  # 403

        if g.user:
            is_root = g.user.roles == 'root'

            if is_root:
                # root can do everything ... he's really cool
                log.debug('root is making changes!')
                node.update(**data)
                node.save()

            else:
                # Ok, so we're not root ...
                incorrect_org = node.organization_id != g.user.organization_id
                incorrect_role = g.user.roles != 'admin'

                if (incorrect_org or incorrect_role):
                    return {"msg": "you are not allowed to edit this node"}, \
                        HTTPStatus.FORBIDDEN  # 403

                # We've established you're an admin for your organisation.
                # Feel free to make some changes to the api_key, name or status
                allowed_attrs = ['name', 'api_key', 'status', 'state']
                node.update(include=allowed_attrs, **data)
                node.save()

        return self.node_schema.dump(node)  # 200


class NodeTasks(ServicesResources):
    """Resource for /api/node/<int:id>/task.
    returns task(s) belonging to a specific node

       Resource for /api/node/<int:id>/task/<int:id>

    TODO do we need the second usage? we can retrieve tasks by the endpoint
    /api/task
    TODO if we do want to keep this, we need to make sure the user only sees
    task that belong to this node
    TODO also the user can only see nodes which belong to their organization
    """

    @with_user_or_node
    @swag_from(str(Path(r"swagger/get_node_tasks.yaml")),
               endpoint='node_tasks')
    def get(self, id):
        """Return a list of tasks for a node or a single task.

        If the query parameter 'state' equals 'open' the list is
        filtered to return only tasks without result.
        """
        # get tasks that belong to node <id>
        node = db.Node.get(id)
        if not node:
            return {"msg": f"node with id={id} not found"}, \
                HTTPStatus.NOT_FOUND  # 404

        s = TaskIncludedSchema() if \
            request.args.get('include') == 'results' else TaskSchema()

        return s.dump(node.collaboration.tasks, many=True).data, HTTPStatus.OK
