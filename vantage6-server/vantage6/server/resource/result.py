# -*- coding: utf-8 -*-
import logging

from flask import g, request
from http import HTTPStatus
from flasgger import swag_from
from pathlib import Path

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
        Result,
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
class Result(ServicesResources):
    """Resource for /api/result"""

    def __init__(self, socketio, mail, api, permissions):
        super().__init__(socketio, mail, api, permissions)
        self.r = getattr(self.permissions, module_name)

    @only_for(['node', 'user', 'container'])
    @swag_from(str(Path(r"swagger/get_result_with_id.yaml")),
               endpoint="result_with_id")
    @swag_from(str(Path(r"swagger/get_result_without_id.yaml")),
               endpoint="result_without_id")
    def get(self, id=None):

        # obtain requisters organization
        if g.user:
            auth_org = g.user.organization
        elif g.node:
            auth_org = g.node.organization
        else:  # g.container
            auth_org = Organization.get(g.container['organization_id'])

        if id:
            result = db_Result.get(id)
            if not result:
                return {'msg': f'Result id={id} not found!'}, \
                    HTTPStatus.NOT_FOUND
            if not self.r.v_glo.can():
                c_orgs = result.task.collaboration.organizations
                if not (self.r.v_org.can() and auth_org in c_orgs):
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED
        else:

            session = DatabaseSessionManager.get_session()
            q = session.query(db_Result)

            if request.args.get('state') == 'open':
                q = q.filter(db_Result.finished_at == None)

            # q = q.join(db_Result)
            if request.args.get('task_id'):
                q = q.filter_by(task_id=request.args.get('task_id'))

            q = q.join(Organization).join(Node).join(Task, db_Result.task)\
                .join(Collaboration)
            if request.args.get('node_id'):
                q = q.filter(db.Node.id == request.args.get('node_id'))\
                    .filter(db.Collaboration.id == db.Node.collaboration_id)

            result = q.all()

            # filter results based on permissions
            if not self.r.v_glo.can():
                if self.r.v_org.can():
                    filtered_result = []
                    for res in result:
                        if res.task.collaboration in auth_org.collaborations:
                            filtered_result.append(res)
                    result = filtered_result
                else:
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED

        if request.args.get('include') == 'task':
            s = result_inc_schema
        else:
            s = result_schema

        return s.dump(result, many=not id).data, HTTPStatus.OK

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
