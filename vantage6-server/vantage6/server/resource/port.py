# -*- coding: utf-8 -*-
import logging

from flask import g, request
from flask_restful import Api
from http import HTTPStatus

from vantage6.common import logger_name
from vantage6.server.permission import (
    PermissionManager,
    Scope as S,
    Operation as P
)
from vantage6.server.resource import (
    with_node,
    ServicesResources
)
from vantage6.server import db
from vantage6.server.resource.common.output_schema import PortSchema
from vantage6.server.resource.common.input_schema import PortInputSchema
from vantage6.server.model import (
    Run,
    AlgorithmPort,
)
from vantage6.server.resource import with_container

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the port resource.

    Parameters
    ----------
    api : Api
        Flask restful api instance
    api_base : str
        Base url of the api
    services : dict
        Dictionary with services required for the resource endpoints
    """
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Ports,
        path,
        endpoint='port_without_id',
        methods=('POST', 'DELETE'),
        resource_class_kwargs=services
    )
    api.add_resource(
        VPNAddress,
        api_base + '/vpn/algorithm/addresses',
        endpoint='vpn_address',
        methods=('GET',),
        resource_class_kwargs=services
    )


# Schemas
port_schema = PortSchema()
port_input_schema = PortInputSchema()


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager) -> None:
    """
    Define the permissions for this resource.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """
    add = permissions.appender(module_name)

    add(scope=S.GLOBAL, operation=P.VIEW, description="view any port")
    add(scope=S.ORGANIZATION, operation=P.VIEW, assign_to_container=True,
        assign_to_node=True, description="view ports of your organizations "
        "collaborations")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class PortBase(ServicesResources):
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)


class Ports(PortBase):
    @with_node
    def post(self):
        """Create a list of port description
        ---
        description: >-
          Creates a description of a port that is available for VPN
          communication for a certain algorithm. Only the node on which the
          algorithm is running is allowed to create this.\n

          This endpoint is not accessible for users, but only for
          authenticated nodes.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  port:
                    type: integer
                    description: Port number that receives container's VPN
                      traffic
                  run_id:
                    type: integer
                    description: Algorithm's run_id
                  label:
                    type: string
                    description: Label for port specified in algorithm
                      docker image

        responses:
          201:
            description: Ok
          401:
            description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["VPN"]
        """
        data = request.get_json()
        # validate request body
        errors = port_input_schema.validate(data)
        if errors:
            return {'msg': 'Request body is incorrect', 'errors': errors}, \
                HTTPStatus.BAD_REQUEST

        # The only entity that is allowed to algorithm ports is the node where
        # those algorithms are running.
        run_id = data['run_id']
        linked_run = g.session.query(Run).filter(Run.id == run_id).one()
        if g.node.id != linked_run.node.id:
            return {'msg': 'You lack the permissions to do that!'},\
                HTTPStatus.UNAUTHORIZED

        port = AlgorithmPort(
            port=data['port'],
            run_id=run_id,
            label=data.get('label' ''),
        )
        port.save()

        return port_schema.dump(port, many=False), HTTPStatus.CREATED

    @with_node
    def delete(self):
        """ Delete ports by run_id
        ---
        description: >-
          Deletes descriptions of a port that is available for VPN
          communication for a certain algorithm. The ports are deleted based
          on run_id. Only the node on which the algorithm is running is
          allowed to delete this. This happens on task completion.\n

          This endpoint is not accessible for users, but only for
          authenticated nodes.

        parameters:
          - in: path
            name: run_id
            schema:
              type: integer
            minimum: 1
            description: Run id for which ports must be deleted
            required: true

        responses:
          200:
            description: Ok
          400:
            description: Run id was not defined
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["VPN"]
        """
        args = request.args
        if 'run_id' not in args:
            return {'msg': 'The run_id argument is required!'}, \
              HTTPStatus.BAD_REQUEST

        # The only entity that is allowed to delete algorithm ports is the node
        # where those algorithms are running.
        run_id = args['run_id']
        linked_run = g.session.query(Run).filter(Run.id == run_id).one()
        if g.node.id != linked_run.node.id:
            return {'msg': 'You lack the permissions to do that!'},\
                HTTPStatus.UNAUTHORIZED

        # all checks passed: delete the port entries
        g.session.query(AlgorithmPort).filter(
            AlgorithmPort.run_id == run_id
        ).delete()
        g.session.commit()

        return {"msg": "Ports removed from the database."}, HTTPStatus.OK


class VPNAddress(ServicesResources):

    @with_container
    def get(self):
        """
        Get a list of the addresses (IP + port) and labels of algorithm
        containers in the same task as the authenticating container.
        ---

        description: >-
          Returns a dictionary of addresses of algorithm containers in the same
          task.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Port|Global|View|❌|❌|View any result|\n
          |Port|Organization|View|❌|✅|View the ports of your
          organizations collaborations|\n

          Not accessible to users.

        parameters:
          - in: path
            name: label
            schema:
              type: string
            description: Algorithm port label to filter by
          - in: path
            name: only_children
            schema:
              type: boolean
            description: Only include the addresses of subtasks, not those at
              the same level. Incompatible with 'only_parent'.
          - in: path
            name: only_parent
            schema:
              type: boolean
            description: Only send the address of the parent task, not those at
              the same level. Incompatible with 'only_children'.
          - in: path
            name: include_children
            schema:
              type: boolean
            description: Include the addresses of subtasks. Ignored if
              'only_children' is True. Incompatible with 'only_parent',
              superseded by 'only_children'.
          - in: path
            name: include_parent
            schema:
              type: boolean
            description: Include the addresses of parent tasks. Ignored if
              'only_parent' is True. Incopatible with 'only_children',
              superseded by 'only_parent'.

        responses:
          200:
            description: Ok
          400:
            description: Incompatible arguments specified

        security:
        - bearerAuth: []

        tags: ["VPN"]
        """
        task_id = g.container['task_id']
        task_ids = [task_id]

        task = db.Task.get(task_id)

        include_children = request.args.get('include_children', False)
        include_parent = request.args.get('include_parent', False)
        only_children = request.args.get('only_children', False)
        only_parent = request.args.get('only_parent', False)

        if only_children and only_parent:
            return {
                'msg': 'Using only_children and only_parent simultaneously is '
                'not possible! Specify one or the other.'
            }, HTTPStatus.BAD_REQUEST
        elif only_children and include_parent:
            return {
                'msg': 'Using only_children and include_parent simultaneously '
                'is not possible! Specify one or the other.'
            }, HTTPStatus.BAD_REQUEST
        elif only_parent and include_children:
            return {
                'msg': 'Using only_parent and include_children simultaneously '
                'is not possible! Specify one or the other.'
            }, HTTPStatus.BAD_REQUEST

        # include child tasks if requested
        if include_children or only_children:
            subtasks = g.session.query(db.Task).filter(
                db.Task.parent_id == task_id
            ).all()
            if only_children:
                task_ids = [t.id for t in subtasks]
            else:
                task_ids.extend([t.id for t in subtasks])

        # include parent task if requested
        if include_parent or only_parent:
            parent = g.session.query(db.Task).filter(
                db.Task.id == task.parent_id
            ).one_or_none()
            if parent:
                if only_parent:
                    task_ids = [parent.id]
                else:
                    task_ids.append(parent.id)

        # get all ports for the tasks requested
        q = g.session.query(AlgorithmPort)\
                     .join(Run)\
                     .filter(Run.task_id.in_(task_ids))\

        # filter by label if requested
        filter_label = request.args.get('label')
        if filter_label:
            q = q.filter(AlgorithmPort.label == filter_label)

        ports = q.all()

        # combine data from ports and nodes
        addresses = []
        for port in ports:
            d = {
                'port': port.port,
                'label': port.label,
                'ip': port.run.node.ip,
                'organization_id': port.run.organization_id,
                'task_id': port.run.task_id,
                'parent_id': port.run.task.parent_id,
            }
            addresses.append(d)

        return {'addresses': addresses}, HTTPStatus.OK
