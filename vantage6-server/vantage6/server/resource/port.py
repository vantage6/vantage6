# -*- coding: utf-8 -*-
import logging

from flask import g, request
from http import HTTPStatus
from sqlalchemy import desc

from vantage6.common import logger_name
from vantage6.server.permission import (
    PermissionManager,
    Scope as S,
    Operation as P
)
from vantage6.server.resource import (
    with_node,
    only_for,
    ServicesResources
)
from vantage6.server.resource.pagination import Pagination
from vantage6.server.resource.common._schema import PortSchema
from vantage6.server.model import (
    Result,
    AlgorithmPort,
    Collaboration,
    Task
)
from vantage6.server.model.base import DatabaseSessionManager


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Ports,
        path,
        endpoint='port_without_id',
        methods=('GET', 'POST', 'DELETE'),
        resource_class_kwargs=services
    )
    api.add_resource(
        Port,
        path + '/<int:id>',
        endpoint='port_with_id',
        methods=('GET',),
        resource_class_kwargs=services
    )


# Schemas
port_schema = PortSchema()


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager):
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

    @only_for(['node', 'user', 'container'])
    def get(self):
        """ Returns a list of ports
        ---

        description: >-
          Returns a list of all ports you are allowed to see.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Port|Global|View|❌|❌|View any result|\n
          |Port|Organization|View|✅|✅|View the ports of your
          organizations collaborations|\n

          Accessible to users.

        parameters:
          - in: query
            name: task_id
            schema:
              type: integer
            description: Task id
          - in: query
            name: result_id
            schema:
              type: integer
            description: Result id
          - in: query
            name: run_id
            schema:
              type: integer
            description: Run id
          - in: query
            name: include
            schema:
              type: string (can be multiple)
            description: Include 'metadata' to get pagination metadata. Note
              that this will put the actual data in an envelope.
          - in: query
            name: page
            schema:
              type: integer
            description: Page number for pagination
          - in: query
            name: per_page
            schema:
              type: integer
            description: Number of items per page

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized

        security:
        - bearerAuth: []

        tags: ["VPN"]
        """
        auth_org = self.obtain_auth_organization()
        args = request.args

        q = DatabaseSessionManager.get_session().query(AlgorithmPort)

        # relation filters
        if 'result_id' in args:
            q = q.filter(AlgorithmPort.result_id == args['result_id'])
        if 'task_id' in args:
            q = q.join(Result).filter(Result.task_id == args['task_id'])
        if 'run_id' in args:
            # check if Result was already joined in 'task_id' arg
            if Result not in [joined.class_ for joined in q._join_entities]:
                q = q.join(Result)
            q = q.join(Task).filter(Task.run_id == args['run_id'])

        # filter based on permissions
        if not self.r.v_glo.can():
            if self.r.v_org.can():
                col_ids = [col.id for col in auth_org.collaborations]
                q = q.filter(Collaboration.id.in_(col_ids))
            else:
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # query the DB and paginate
        q = q.order_by(desc(AlgorithmPort.id))
        page = Pagination.from_query(query=q, request=request)

        # serialization of the models
        s = port_schema

        return self.response(page, s)

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
                  result_id:
                    type: integer
                    description: Algorithm's result_id
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

        # The only entity that is allowed to algorithm ports is the node where
        # those algorithms are running.
        result_id = data.get('result_id', '')
        linked_result = DatabaseSessionManager.get_session().query(
            Result).filter(Result.id == result_id).one()
        if g.node.id != linked_result.node.id:
            return {'msg': 'You lack the permissions to do that!'},\
                HTTPStatus.UNAUTHORIZED

        port = AlgorithmPort(
            port=data.get('port', ''),
            result_id=result_id,
            label=data.get('label' ''),
        )
        port.save()

        return port_schema.dump(port, many=False).data, HTTPStatus.CREATED

    @with_node
    def delete(self):
        # FIXME should we have swagger docs if only accessible for node? Also
        # same case for post request
        """ Delete ports by result_id
        ---
        description: >-
          Deletes descriptions of a port that is available for VPN
          communication for a certain algorithm. The ports are deleted based
          on result_id. Only the node on which the algorithm is running is
          allowed to delete this. This happens on task completion.\n

          This endpoint is not accessible for users, but only for
          authenticated nodes.

        parameters:
          - in: path
            name: result_id
            schema:
              type: integer
            minimum: 1
            description: Result id for which ports must be deleted
            required: true

        responses:
          200:
            description: Ok
          400:
            description: Result id was not defined
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["VPN"]
        """
        args = request.args
        if 'result_id' not in args:
            return {'msg': 'The result_id argument is required!'}, \
              HTTPStatus.BAD_REQUEST

        # The only entity that is allowed to delete algorithm ports is the node
        # where those algorithms are running.
        result_id = args['result_id']
        linked_result = DatabaseSessionManager.get_session().query(
            Result).filter(Result.id == result_id).one()
        if g.node.id != linked_result.node.id:
            return {'msg': 'You lack the permissions to do that!'},\
                HTTPStatus.UNAUTHORIZED

        # all checks passed: delete the port entries
        session = DatabaseSessionManager.get_session()
        session.query(AlgorithmPort).filter(
            AlgorithmPort.result_id == result_id
        ).delete()
        session.commit()

        return {"msg": "Ports removed from the database."}, HTTPStatus.OK


class Port(PortBase):
    """Resource for /api/port"""

    @only_for(['node', 'user', 'container'])
    def get(self, id):
        """ Get a single port
        ---
        description: >-
            Returns a port specified by an id.\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Port|Global|View|❌|❌|View any port|\n
            |Port|Organization|View|✅|✅|View the ports of your
            organization's collaborations|\n

            Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            minimum: 1
            description: Port id
            required: true

        responses:
          200:
              description: Ok
          401:
              description: Unauthorized
          404:
              description: Port id not found

        security:
          - bearerAuth: []

        tags: ["VPN"]
        """
        auth_org = self.obtain_auth_organization()

        port = AlgorithmPort.get(id)
        if not port:
            return {'msg': f'Port id={id} not found!'}, HTTPStatus.NOT_FOUND

        # check permissions
        if not self.r.v_glo.can():
            if not self.r.v_org.can() and auth_org == auth_org.id:
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # serialize
        s = port_schema

        return s.dump(port, many=False).data, HTTPStatus.OK
