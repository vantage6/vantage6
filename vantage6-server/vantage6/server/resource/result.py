# -*- coding: utf-8 -*-
import logging

from flask import g, request
from http import HTTPStatus
from flasgger import swag_from
from pathlib import Path

from vantage6.server import db
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
from vantage6.server.model.base import Database


module_name = __name__.split('.')[-1]
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


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Result(ServicesResources):
    """Resource for /api/result"""

    @only_for(['node', 'user', 'container'])
    @swag_from(str(Path(r"swagger/get_result_with_id.yaml")),
               endpoint="result_with_id")
    @swag_from(str(Path(r"swagger/get_result_without_id.yaml")),
               endpoint="result_without_id")
    def get(self, id=None):
        if id:
            t = db_Result.get(id)
        else:

            session = Database().Session
            q = session.query(db_Result)

            if request.args.get('state') == 'open':
                q = q.filter(db_Result.finished_at is None)

            # q = q.join(db_Result)
            if request.args.get('task_id'):
                q = q.filter_by(task_id=request.args.get('task_id'))

            q = q.join(Organization).join(Node).join(Task, db_Result.task)\
                .join(Collaboration)
            if request.args.get('node_id'):
                q = q.filter(db.Node.id == request.args.get('node_id'))\
                    .filter(db.Collaboration.id == db.Node.collaboration_id)

            t = q.all()

        if request.args.get('include') == 'task':
            s = result_inc_schema
        else:
            s = result_schema

        return s.dump(t, many=not bool(id)).data, HTTPStatus.OK

    @with_node
    @swag_from(str(Path(r"swagger/patch_result_with_id.yaml")),
               endpoint="result_with_id")
    def patch(self, id):
        """Update a Result."""
        data = request.get_json()
        result = db_Result.get(id)

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
        self.socketio.emit(
            "status_update",
            {'result_id': id},
            room='collaboration_'+str(result.task.collaboration.id),
            namespace='/tasks',
        )

        result.started_at = parse_datetime(data.get("started_at"),
                                           result.started_at)
        result.finished_at = parse_datetime(data.get("finished_at"))
        result.result = data.get("result")
        result.log = data.get("log")
        result.save()

        return result
