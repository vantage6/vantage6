import logging
from http import HTTPStatus

from flask import g, request
from flask_restful import Api
from marshmallow import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.sql.selectable import Select

from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmStepType, RunStatus, TaskStatusQueryOptions

from vantage6.backend.common.resource.pagination import Pagination

from vantage6.server import db
from vantage6.server.model import Collaboration, Node, Organization, Run as db_Run, Task
from vantage6.server.permission import (
    Operation as P,
    PermissionManager,
    RuleCollection,
    Scope as S,
)
from vantage6.server.resource import (
    ServicesResources,
    only_for,
    with_node,
)
from vantage6.server.resource.common.input_schema import RunInputSchema
from vantage6.server.resource.common.output_schema import (
    ResultSchema,
    RunSchema,
    RunTaskIncludedSchema,
)
from vantage6.server.utils import parse_datetime

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the run resource.

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
        Runs,
        path,
        endpoint="run_without_id",
        methods=("GET",),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Run,
        path + "/<int:id>",
        endpoint="run_with_id",
        methods=("GET", "PATCH"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Results,
        api_base + "/result",
        endpoint="result_without_id",
        methods=("GET",),
        resource_class_kwargs=services,
    )
    # TODO v4+ implement a PATCH method and use it to update the result. Then,
    # remove that from patching it in the Run resource.
    api.add_resource(
        Result,
        api_base + "/result/<int:id>",
        endpoint="result_with_id",
        methods=("GET",),
        resource_class_kwargs=services,
    )


# Schemas
run_schema = RunSchema()
run_inc_schema = RunTaskIncludedSchema()
result_schema = ResultSchema()
run_input_schema = RunInputSchema()


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager):
    """
    Define the permissions for this resource.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """
    add = permissions.appender(module_name)

    add(scope=S.GLOBAL, operation=P.VIEW, description="view any run")
    add(
        scope=S.COLLABORATION,
        operation=P.VIEW,
        assign_to_container=True,
        assign_to_node=True,
        description="view runs of your organizations collaborations",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.VIEW,
        description="view any run of a task created by your organization",
    )
    add(
        scope=S.OWN,
        operation=P.VIEW,
        description="view any run of a task created by you",
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class RunBase(ServicesResources):
    """Base class for run resources"""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)


class MultiRunBase(RunBase):
    """Base class for resources that return multiple runs or results"""

    def get_query_multiple_runs(self) -> Select | tuple:
        """
        Returns a sqlalchemy selection object that can be used to retrieve runs.

        Returns
        -------
        sqlalchemy.sql.selectable.Select or tuple
            A query object to retrieve a single algorithm run, or a tuple with
            a message and HTTP error code if the query could not be set up
        """
        auth_org = self.obtain_auth_organization()
        args = request.args
        log.debug(f"Querying runs with args: {args}")

        q = select(db_Run)

        if "organization_id" in args:
            if not self.r.allowed_for_org(P.VIEW, args["organization_id"]):
                return {
                    "msg": "You lack the permission to view runs for "
                    f"organization id={args['organization_id']}!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db_Run.organization_id == args["organization_id"])

        if "task_id" in args:
            task = db.Task.get(args["task_id"])
            if not task:
                return {
                    "msg": f"Task id={args['task_id']} does not exist!"
                }, HTTPStatus.BAD_REQUEST
            elif not self.r.allowed_for_org(P.VIEW, task.init_org_id) and not (
                self.r.v_own.can() and g.user.id == task.init_user_id
            ):
                return {
                    "msg": "You lack the permission to view runs for "
                    f"task id={args['task_id']}!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db_Run.task_id == args["task_id"])

        if args.get("node_id"):
            node = db.Node.get(args["node_id"])
            if not node:
                return {
                    "msg": f"Node id={args['node_id']} does not exist!"
                }, HTTPStatus.BAD_REQUEST
            elif not self.r.can_for_col(P.VIEW, node.collaboration_id):
                return {
                    "msg": "You lack the permission to view runs for "
                    f"node id={args['node_id']}!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db.Node.id == args.get("node_id")).filter(
                db.Collaboration.id == db.Node.collaboration_id
            )

        # relation filters
        if "port" in args:
            q = q.filter(db_Run.port == args["port"])

        # date selections
        for param in ["assigned", "started", "finished"]:
            if f"{param}_till" in args:
                q = q.filter(getattr(db_Run, f"{param}_at") <= args[f"{param}_till"])
            if f"{param}_from" in args:
                q = q.filter(db_Run.assigned_at >= args[f"{param}_from"])

        q = q.join(Organization).join(Node).join(Task, db_Run.task).join(Collaboration)

        # The state can be one of the following:
        #   open:
        #       Runs that are not finished and all depending runs from all tasks are
        #       completed or do not exist
        #   waiting:
        #       Runs that are not finished and depending runs are not completed
        #   finished:
        #       Runs that are finished
        #
        if args.get("state") == TaskStatusQueryOptions.OPEN:
            q = q.filter(db.Task.is_open)
        elif args.get("state") == TaskStatusQueryOptions.WAITING:
            q = q.filter(db.Task.is_waiting)
        elif args.get("state") == TaskStatusQueryOptions.FINISHED:
            q = q.filter(db_Run.finished_at.isnot(None))

        if "collaboration_id" in args:
            if not self.r.can_for_col(P.VIEW, args["collaboration_id"]):
                return {
                    "msg": "You lack the permission to view runs for "
                    f"collaboration id={args['collaboration_id']}!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(Collaboration.id == args["collaboration_id"])

        # filter based on permissions
        if not self.r.v_glo.can():
            if self.r.v_col.can():
                col_ids = [col.id for col in auth_org.collaborations]
                q = q.filter(Collaboration.id.in_(col_ids))
            elif self.r.v_org.can():
                q = q.filter(Organization.id == auth_org.id)
            elif self.r.v_own.can():
                q = q.filter(Task.init_user_id == g.user.id)
            else:
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        # query the DB and paginate
        q = q.order_by(desc(db_Run.id))
        return q


class Runs(MultiRunBase):
    @only_for(("node", "user", "container"))
    def get(self):
        """Returns a list of runs
        ---

        description: >-
            Returns a list of all runs you are allowed to see.\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Run|Global|View|❌|❌|View any run|\n
            |Run|Collaboration|View|✅|✅|View the runs of your
            organization's collaborations|\n
            |Run|Organization|View|❌|❌|View any run from a task created by
            your organization|\n
            |Run|Own|View|❌|❌|View any run from a task created by you|\n

            Accessible to users.

        parameters:
            - in: query
              name: task_id
              schema:
                type: integer
              description: Task id
            - in: query
              name: organization_id
              schema:
                type: integer
              description: Organization id
            - in: query
              name: collaboration_id
              schema:
                type: integer
              description: Collaboration id
            - in: query
              name: assigned_from
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task assigned from this date
            - in: query
              name: started_from
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task started from this date
            - in: query
              name: finished_from
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task finished from this date
            - in: query
              name: assigned_till
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task assigned till this date
            - in: query
              name: started_till
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task started till this date
            - in: query
              name: finished_till
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task finished till this date
            - in: query
              name: state
              schema:
                type: string
              description: The state of the task ('open')
            - in: query
              name: node_id
              schema:
                type: integer
              description: Node id
            - in: query
              name: port
              schema:
                type: integer
              description: Port number
            - in: query
              name: include
              schema:
                type: string (can be multiple)
              description: Include 'task' to include task data.
            - in: query
              name: page
              schema:
                type: integer
              description: Page number for pagination (default 1)
            - in: query
              name: per_page
              schema:
                type: integer
              description: Number of items per page (default 10)
            - in: query
              name: sort
              schema:
                type: string
              description: >-
                Sort by one or more fields, separated by a comma. Use a minus
                sign (-) in front of the field to sort in descending order.

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized
          400:
            description: Improper values for pagination or sorting parameters

        security:
        - bearerAuth: []

        tags: ["Algorithm"]
        """
        query = self.get_query_multiple_runs()

        # If no query is returned, we should return message and error code
        if not isinstance(query, Select):
            return query

        try:
            page = Pagination.from_query(query, request, db.Run)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        # serialization of the models
        s = run_inc_schema if self.is_included("task") else run_schema

        return self.response(page, s)


class Results(MultiRunBase):
    @only_for(("node", "user", "container"))
    def get(self):
        """Returns a list of results
        ---

        description: >-
            Returns a list of all results you are allowed to see.\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Run|Global|View|❌|❌|View any result|\n
            |Run|Collaboration|View|✅|✅|View the results of your
            organization's collaborations|\n
            |Run|Organization|View|❌|❌|View any result from a task created
            by your organization|\n
            |Run|Own|View|❌|❌|View any result from a task created by you|\n

            Accessible to users.

        parameters:
            - in: query
              name: task_id
              schema:
                type: integer
              description: Task id
            - in: query
              name: organization_id
              schema:
                type: integer
              description: Organization id
            - in: query
              name: collaboration_id
              schema:
                type: integer
              description: Collaboration id
            - in: query
              name: assigned_from
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task assigned from this date
            - in: query
              name: started_from
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task started from this date
            - in: query
              name: finished_from
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task finished from this date
            - in: query
              name: assigned_till
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task assigned till this date
            - in: query
              name: started_till
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task started till this date
            - in: query
              name: finished_till
              schema:
                type: date (yyyy-mm-dd)
              description: Show only task finished till this date
            - in: query
              name: state
              schema:
                type: string
              description: The state of the task ('open')
            - in: query
              name: node_id
              schema:
                type: integer
              description: Node id
            - in: query
              name: port
              schema:
                type: integer
              description: Port number
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
            - in: query
              name: sort
              schema:
                type: string
              description: >-
                Sort by one or more fields, separated by a comma. Use a minus
                sign (-) in front of the field to sort in descending order.

        responses:
            200:
                description: Ok
            401:
                description: Unauthorized

        security:
        - bearerAuth: []

        tags: ["Algorithm"]
        """
        query = self.get_query_multiple_runs()

        # If no query is returned, we should return message and error code
        if not isinstance(query, Select):
            return query

        try:
            page = Pagination.from_query(query, request, db.Run)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        return self.response(page, result_schema)


class SingleRunBase(RunBase):
    """Base class for resources that return a single run or result"""

    def get_single_run(self, id) -> db_Run | tuple:
        """
        Set up a query to retrieve a single algorithm run

        Parameters
        ----------
        id : int
            The id of the run to retrieve

        Returns
        -------
        db.Run | tuple
            An algorithm Run object, or a tuple with a message and HTTP error
            code if the Run could not be retrieved
        """
        run = db_Run.get(id)
        if not run:
            return {"msg": f"Run id={id} not found!"}, HTTPStatus.NOT_FOUND

        if not self.r.allowed_for_org(P.VIEW, run.task.init_org_id) and not (
            self.r.v_own.can() and run.task.init_user_id == g.user.id
        ):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED
        return run


class Run(SingleRunBase):
    """Resource for /api/run"""

    @only_for(("node", "user", "container"))
    def get(self, id):
        """Get a single run's data
        ---

        description: >-
            Returns a run from a task specified by an id. \n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Run|Global|View|❌|❌|View any run|\n
            |Run|Collaboration|View|✅|✅|View the runs of your
            organization's collaborations|\n
            |Run|Organization|View|❌|❌|View any run from a task created by
            your organization|\n
            |Run|Own|View|❌|❌|View any run from a task created by you|\n

            Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            minimum: 1
            description: Task id
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
              description: Unauthorized
          404:
              description: Run id not found

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """
        run = self.get_single_run(id)

        # return error code if run is not found
        if not isinstance(run, db_Run):
            return run

        s = run_inc_schema if request.args.get("include") == "task" else run_schema

        return s.dump(run, many=False), HTTPStatus.OK

    @with_node
    def patch(self, id):
        """Update algorithm run data, for example to update the result
        ---
        description: >-
          Update runs from the node. Only done if the request comes from the
          correct, authenticated node.\n

          The user cannot access this endpoint so they cannot tamper with any
          runs.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
              minimum: 1
            description: Task id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  started_at:
                    type: string
                    description: Time at which task was started
                  finished_at:
                    type: string
                    description: Time at which task was completed
                  result:
                    type: string
                    description: (Encrypted) result of the task
                  log:
                    type: string
                    description: Task log messages
                  status:
                    type: string
                    description: Status of the task

        responses:
          200:
            description: Ok
          400:
            description: Run already posted
          401:
            description: Unauthorized
          404:
            description: Run id not found

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """
        run: db_Run = db_Run.get(id)
        if not run:
            return {"msg": f"Run id={id} not found!"}, HTTPStatus.NOT_FOUND

        data = request.get_json(silent=True)
        # validate request body
        try:
            data = run_input_schema.load(data, partial=True)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        if run.organization_id != g.node.organization_id:
            log.warning(
                "Node %s tries to update a run that does not belong to them.",
                g.node.name,
            )
            log.warning("    Run organization: %s", run.organization_id)
            log.warning("    Node organization: %s", g.node.organization)
            return {
                "msg": "This is not your algorithm run to PATCH!"
            }, HTTPStatus.UNAUTHORIZED

        if run.finished_at is not None:
            # For killed runs, allow updating only the logs. This is allowed because
            # finished_at is by the server to the time the run was killed, but then the
            # node can still send logs. For all other statuses, we do not allow
            # updating the run when it is done.
            if run.status == RunStatus.KILLED.value:
                # check if only log is provided
                if len(data) > 1 or data.get("log") is None:
                    return {
                        "msg": "Only the log can be updated for a killed run!"
                    }, HTTPStatus.BAD_REQUEST
                # update the log
                run.log = data.get("log")
                run.save()
                return run_schema.dump(run, many=False), HTTPStatus.OK
            else:
                return {
                    "msg": "Cannot update an already finished algorithm run!"
                }, HTTPStatus.BAD_REQUEST

        run.started_at = parse_datetime(data.get("started_at"), run.started_at)
        run.finished_at = parse_datetime(data.get("finished_at"))
        run.result = data.get("result")
        run.log = data.get("log")
        run.status = data.get("status", run.status)
        run.save()

        # In case there are dependent tasks and the current task has failed,
        # we should mark the dependent tasks as failed as well.
        if RunStatus.has_failed(run.status):
            dependent_tasks = run.task.required_by
            # add dependent tasks recursively
            if dependent_tasks:
                dependent_tasks = self._add_dependent_tasks(dependent_tasks)

            for dependent_task in dependent_tasks:
                log.debug(f"Marking dependent task {dependent_task.id} runs as failed.")
                # Also mark all dependent runs as failed
                for dependent_run in dependent_task.runs:
                    dependent_run.status = RunStatus.DEPENDED_ON_FAILED_TASK.value
                    dependent_run.finished_at = run.finished_at
                    dependent_run.save()

        # notify collaboration nodes/users that the task has an update
        # TODO refactor it shouldn't be necessary to send two events.
        self.socketio.emit(
            "status_update",
            {"run_id": id},
            namespace="/tasks",
            room=f"collaboration_{run.task.collaboration.id}",
        )

        self.socketio.emit(
            "algorithm_status_change",
            {
                "run_id": run.id,
                "status": run.status,
                "task_id": run.task.id,
                "job_id": run.task.job_id,
                "collaboration_id": run.task.collaboration.id,
                "node_id": run.node.id,
                "organization_id": run.organization.id,
                "parent_id": run.task.parent_id,
            },
            namespace="/tasks",
            room=f"collaboration_{run.task.collaboration.id}",
        )

        return run_schema.dump(run, many=False), HTTPStatus.OK

    def _add_dependent_tasks(self, dependent_tasks: list[db.Task]) -> list[db.Task]:
        """Recursively add all dependent tasks to the list of dependent tasks"""
        for dependent_task in dependent_tasks:
            if dependent_task.required_by:
                for deeper_dependent_task in dependent_task.required_by:
                    if deeper_dependent_task not in dependent_tasks:
                        # Skip the mark as failed for tasks that are compute tasks, as
                        # these might still be able to run.
                        if AlgorithmStepType.is_compute(deeper_dependent_task.action):
                            continue

                        dependent_tasks.append(deeper_dependent_task)
                        dependent_tasks = self._add_dependent_tasks(dependent_tasks)
        return dependent_tasks


class Result(SingleRunBase):
    """Resource for /api/result/<id>"""

    @only_for(("node", "user", "container"))
    def get(self, id):
        """Get a single result
        ---

        description: >-
            Returns a result specified by an algorithm run id. \n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Run|Global|View|❌|❌|View any result|\n
            |Run|Collaboration|View|✅|✅|View the results of your
            organization's collaborations|\n
            |Run|Organization|View|❌|❌|View any result from a task created
            by your organization|\n
            |Run|Own|View|❌|❌|View any result from a task created by you|\n

            Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            minimum: 1
            description: Algorithm run id
            required: true

        responses:
          200:
              description: Ok
          401:
              description: Unauthorized
          404:
              description: Run id not found

        security:
          - bearerAuth: []

        tags: ["Algorithm"]
        """
        run = self.get_single_run(id)

        # return error code if run is not found
        if not isinstance(run, db_Run):
            return run

        return result_schema.dump(run, many=False), HTTPStatus.OK
