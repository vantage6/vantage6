# -*- coding: utf-8 -*-
import logging

from flask import g, request
from http import HTTPStatus
from flasgger import swag_from
from pathlib import Path
from sqlalchemy import desc

from vantage6.common import logger_name
from vantage6.server import db
from vantage6.server.permission import (
    PermissionManager,
    Scope as S,
    Operation as P
)
from vantage6.server.resource import (
    with_node,
    only_for,
    parse_datetime,
    ServicesResources
)
from vantage6.server.resource.pagination import Pagination
from vantage6.server.resource._schema import (
    ResultSchema,
    ResultTaskIncludedSchema
)
from vantage6.server.model import (
    Result as db_Result,
    Node,
    Task,
    Collaboration,
    Organization
)
from vantage6.server.model.base import DatabaseSessionManager


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Results,
        path,
        endpoint='result_without_id',
        methods=('GET',),
        resource_class_kwargs=services
    )
    api.add_resource(
        Result,
        path + '/<int:id>',
        endpoint='result_with_id',
        methods=('GET', 'PATCH'),
        resource_class_kwargs=services
    )


# Schemas
result_schema = ResultSchema()
result_inc_schema = ResultTaskIncludedSchema()


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager):
    add = permissions.appender(module_name)

    add(scope=S.GLOBAL, operation=P.VIEW,
        description="view any result")
    add(scope=S.ORGANIZATION, operation=P.VIEW, assign_to_container=True,
        assign_to_node=True, description="view results of your organizations "
        "collaborations")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class ResultBase(ServicesResources):

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)


class Results(ResultBase):

    @only_for(['node', 'user', 'container'])
    def get(self):
        """ Returns a list of results
        ---

        description: >-
            Returns a list of all results only if the node, user or container
            have the proper authorization to do so.\n\n

            ### Permission Table\n
            |Rulename|Scope|Operation|Node|Container|Description|\n
            |--|--|--|--|--|--|\n
            |Result|Global|View|❌|❌|View any result|\n
            |Result|Organization|View|✅|✅|View the results of your
            organizations collaborations|\n\n

            Accesible as: `node` , `user` and `container`.\n\n

            Results can be paginated by using the parameter `page`. The
            pagination metadata can be included using `include=metadata`, note
            that this will put the actual data in an envelope.

        parameters:
            - in: query
              name: task_id
              schema:
                type: integer
              description: task id
            - in: query
              name: organization_id
              schema:
                type: integer
              description: organization id
            - in: query
              name: assigned_from
              schema:
                type: date (yyyy-mm-dd)
              description: show only task assigned from this date
            - in: query
              name: started_from
              schema:
                type: date (yyyy-mm-dd)
              description: show only task started from this date
            - in: query
              name: finished_from
              schema:
                type: date (yyyy-mm-dd)
              description: show only task finished from this date
            - in: query
              name: assigned_till
              schema:
                type: date (yyyy-mm-dd)
              description: show only task assigned till this date
            - in: query
              name: started_till
              schema:
                type: date (yyyy-mm-dd)
              description: show only task started till this date
            - in: query
              name: finished_till
              schema:
                type: date (yyyy-mm-dd)
              description: show only task finished till this date
            - in: query
              name: state
              schema:
                type: string
              description: the state of the task ('open')
            - in: query
              name: node_id
              schema:
                type: integer
              description: node id
            - in: query
              name: include
              schema:
                type: string (can be multiple)
              description: what to include ('task', 'metadata')
            - in: query
              name: page
              schema:
                type: integer
              description: page number for pagination
            - in: query
              name: per_page
              schema:
                type: integer
              description: number of items per page

        responses:
            200:
                description: Ok
            401:
                description: Unauthorized

        security:
        - bearerAuth: []

        tags: ["Result"]
        """
        auth_org = self.obtain_auth_organization()
        args = request.args

        q = DatabaseSessionManager.get_session().query(db_Result)

        # relation filters
        for param in ['task_id', 'organization_id']:
            if param in args:
                q = q.filter(getattr(db_Result, param) == args[param])

        # date selections
        for param in ['assigned', 'started', 'finished']:
            if f'{param}_till' in args:
                q = q.filter(getattr(db_Result, f'{param}_at')
                             <= args[f'{param}_till'])
            if f'{param}_from' in args:
                q = q.filter(db_Result.assigned_at >= args[f'{param}_from'])

        # custom filters
        if args.get('state') == 'open':
            q = q.filter(db_Result.finished_at == None)

        q = q.join(Organization).join(Node).join(Task, db_Result.task)\
            .join(Collaboration)

        if args.get('node_id'):
            q = q.filter(db.Node.id == args.get('node_id'))\
                .filter(db.Collaboration.id == db.Node.collaboration_id)

        # filter based on permissions
        if not self.r.v_glo.can():
            if self.r.v_org.can():
                col_ids = [col.id for col in auth_org.collaborations]
                q = q.filter(Collaboration.id.in_(col_ids))
            else:
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # query the DB and paginate
        q = q.order_by(desc(db_Result.id))
        page = Pagination.from_query(query=q, request=request)

        # serialization of the models
        s = result_inc_schema if self.is_included('task') else result_schema

        return self.response(page, s)


class Result(ResultBase):
    """Resource for /api/result"""

    @only_for(['node', 'user', 'container'])
    def get(self, id):
        """ Get a single result
        ---

        description: >-
            Returns a result from a task specified by an id. \n\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Node|Container|Description|\n
            |--|--|--|--|--|--|\n
            |Result|Global|View|❌|❌|View any result|\n
            |Result|Organization|View|✅|✅|View the results of your
            organizations collaborations|\n

            Accessable as: `node`, `user` and `container`.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            minimum: 1
            description: unique task identifier
            required: true
          - in: query
            name: include
            schema:
              type: string
            description: what to include ('task')

        responses:
          200:
              description: Ok
          401:
              description: Unauthorized or missing permission
          404:
              description: result id not found

        security:
          - bearerAuth: []

        tags: ["Result"]
        """

        auth_org = self.obtain_auth_organization()

        result = db_Result.get(id)
        if not result:
            return {'msg': f'Result id={id} not found!'}, \
                HTTPStatus.NOT_FOUND
        if not self.r.v_glo.can():
            c_orgs = result.task.collaboration.organizations
            if not (self.r.v_org.can() and auth_org in c_orgs):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        s = result_inc_schema if request.args.get('include') == 'task' \
            else result_schema

        return s.dump(result, many=False).data, HTTPStatus.OK

    @with_node
    @swag_from(str(Path(r"swagger/patch_result_with_id.yaml")),
               endpoint="result_with_id")
    def patch(self, id):
        """Update a Result."""
        result = db_Result.get(id)
        if not result:
            return {'msg': f'Result id={id} not found!'}, HTTPStatus.NOT_FOUND

        data = request.get_json()

        if result.organization_id != g.node.organization_id:
            log.warn(
                f"{g.node.name} tries to update a result that does not belong "
                f"to him. ({result.organization_id}/{g.node.organization_id})"
            )
            return {"msg": "This is not your result to PATCH!"}, \
                HTTPStatus.UNAUTHORIZED

        if result.finished_at is not None:
            return {"msg": "Cannot update an already finished result!"}, \
                HTTPStatus.BAD_REQUEST

        # notify collaboration nodes/users that the task has an update
        self.socketio.emit("status_update", {'result_id': id},
                           namespace='/tasks', room='collaboration_' +
                           str(result.task.collaboration.id))

        result.started_at = parse_datetime(data.get("started_at"),
                                           result.started_at)
        result.finished_at = parse_datetime(data.get("finished_at"))
        result.result = data.get("result")
        result.log = data.get("log")
        result.save()

        return result_schema.dump(result, many=False).data, HTTPStatus.OK
