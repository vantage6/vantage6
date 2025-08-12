import logging
from http import HTTPStatus

from flask import g, request
from flask_restful import Api
from sqlalchemy import desc, select
from sqlalchemy.sql import visitors

from vantage6.common.enum import (
    TaskStatus,
)

from vantage6.backend.common.resource.pagination import Pagination

from vantage6.server import db
from vantage6.server.permission import (
    Operation as P,
    PermissionManager,
    RuleCollection,
    Scope as S,
)
from vantage6.server.resource import only_for, with_user
from vantage6.server.resource.common.output_schema import (
    TaskSchema,
    TaskWithResultSchema,
    TaskWithRunAndResultSchema,
    TaskWithRunSchema,
)
from vantage6.server.resource.common.task_post_base import TaskPostBase
from vantage6.server.resource.event import kill_task

module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the task resource.

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
        Tasks,
        path,
        endpoint="task_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Task,
        path + "/<int:id>",
        endpoint="task_with_id",
        methods=("GET", "DELETE"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        TaskStatusEndpoint,
        path + "/<int:task_id>/status",
        endpoint="task_status",
        methods=("GET",),
        resource_class_kwargs=services,
    )


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

    add(scope=S.GLOBAL, operation=P.VIEW, description="view any task")
    add(
        scope=S.COLLABORATION,
        operation=P.VIEW,
        assign_to_container=True,
        assign_to_node=True,
        description="view tasks of your collaborations",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.VIEW,
        description="view tasks that your organization initiated",
    )
    add(scope=S.OWN, operation=P.VIEW, description="view tasks that you initiated")

    add(scope=S.GLOBAL, operation=P.CREATE, description="create a new task")
    add(
        scope=S.COLLABORATION,
        operation=P.CREATE,
        description=(
            "create a new task for collaborations in which your organization "
            "participates with"
        ),
    )

    add(scope=S.GLOBAL, operation=P.DELETE, description="delete a task")
    add(
        scope=S.COLLABORATION,
        operation=P.DELETE,
        description="delete a task from your collaborations",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.DELETE,
        description=(
            "delete a task from a collaboration in which your organization "
            "participates with"
        ),
    )
    add(scope=S.OWN, operation=P.DELETE, description="delete tasks that you created")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
task_schema = TaskSchema()
task_run_schema = TaskWithRunSchema()
task_result_schema = TaskWithResultSchema()
task_result_run_schema = TaskWithRunAndResultSchema()


class TaskBase(TaskPostBase):
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)
        # permissions for the run resource are also relevant for the task
        # resource as they are sometimes included
        self.r_run: RuleCollection = getattr(self.permissions, "run")

    def _select_schema(self) -> TaskSchema:
        """
        Select the schema to use for serialization.

        Returns
        -------
        TaskSchema
            Schema to use for serialization
        """
        if self.is_included("runs") and self.is_included("results"):
            return task_result_run_schema
        elif self.is_included("runs"):
            return task_run_schema
        elif self.is_included("results"):
            return task_result_schema
        else:
            return task_schema


class Tasks(TaskBase):
    @only_for(("user", "node", "container"))
    def get(self):
        """List tasks
        ---
        description: >-
          Returns a list of tasks.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Task|Global|View|❌|❌|View any task|\n
          |Task|Collaboration|View|✅|✅|View any task in your collaborations|
          \n
          |Task|Organization|View|❌|❌|View any task that your organization
          created|\n
          |Task|Own|View|❌|❌|View any task that you created|\n

          Accessible to users.

        parameters:
          - in: query
            name: init_org_id
            schema:
              type: int
            description: The organization id of the origin of the request
          - in: query
            name: init_user_id
            schema:
              type: int
            description: The user id of the user that started the task
          - in: query
            name: collaboration_id
            schema:
              type: int
            description: The collaboration id to which the task belongs
          - in: query
            name: study_id
            schema:
              type: int
            description: The study id to which the task belongs
          - in: query
            name: is_user_created
            schema:
              type: int
            description: >-
              If larger than 0, returns tasks created by a user (top-level
              tasks). If equal to 0, returns subtask created by an algorithm.
              If not specified, both are returned.
          - in: query
            name: image
            schema:
              type: str
            description: >-
              (Docker) image name which is used in the task. Name to match
              with a LIKE operator. \n
              * The percent sign (%) represents zero, one, or multiple
              characters\n
              * underscore sign (_) represents one, single character
          - in: query
            name: parent_id
            schema:
              type: int
            description: The id of the parent task
          - in: query
            name: job_id
            schema:
              type: int
            description: The run id that belongs to the task
          - in: query
            name: store_id
            schema:
              type: int
            description: The algorithm store ID from which the algorithm was retrieved
          - in: query
            name: name
            schema:
              type: str
            description: >-
              Name to match with a LIKE operator. \n
              * The percent sign (%) represents zero, one, or multiple
              characters\n
              * underscore sign (_) represents one, single character
          - in: query
            name: description
            schema:
              type: string
            description: >-
              Description to match with a LIKE operator. \n
              * The percent sign (%) represents zero, one, or multiple
              characters\n
              * underscore sign (_) represents one, single character
          - in: query
            name: database
            schema:
              type: string
            description: >-
              Database description to match with a LIKE operator. \n
              * The percent sign (%) represents zero, one, or multiple
              characters\n
              * underscore sign (_) represents one, single character
          - in: query
            name: run_id
            schema:
              type: int
            description: A run id that belongs to the task
          - in: query
            name: include
            schema:
              type: array
              items:
                type: string
            description: Include 'results' to include the task's results,
              'runs' to include details on algorithm runs. For including
               multiple, do either `include=x,y` or `include=x&include=y`.
          - in: query
            name: status
            schema:
              type: string
            description: Filter by task status, e.g. 'active' for active
              tasks, 'completed' for finished or 'crashed' for failed tasks.
          - in: query
            name: session_id
            schema:
              type: int
            description: A session id that belongs to the task
          - in: query
            name: dataframe_id
            schema:
                type: int
            description: Dataframe ID
          - in: query
            name: page
            schema:
              type: integer
            description: Page number for pagination (default=1)
          - in: query
            name: per_page
            schema:
              type: integer
            description: Number of items per page (default=10)
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
          400:
            description: Non-allowed or wrong parameter values
          401:
            description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["Task"]
        """
        q = select(db.Task)
        args = request.args

        auth_org_id = self.obtain_organization_id()

        # check permissions and apply filter if neccassary
        if not self.r.v_glo.can():
            if self.r.v_col.can():
                q = (
                    q.join(db.Collaboration)
                    .join(db.Organization)
                    .filter(db.Collaboration.organizations.any(id=auth_org_id))
                )
            elif self.r.v_org.can():
                q = q.join(db.Organization).filter(db.Task.init_org_id == auth_org_id)
            elif self.r.v_own.can():
                q = q.filter(db.Task.init_user_id == g.user.id)
            else:
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED
        # if results are included, check permissions on results
        if self.is_included("results"):
            max_scope_task = self.r.get_max_scope(P.VIEW)
            if not self.r_run.has_at_least_scope(max_scope_task, P.VIEW):
                max_scope_run = self.r_run.get_max_scope(P.VIEW)
                return {
                    "msg": "You cannot view the results of all tasks, as you "
                    f"are allowed to view tasks with scope {max_scope_task} "
                    f"but you can only view results with scope {max_scope_run}"
                }, HTTPStatus.UNAUTHORIZED

        if "collaboration_id" in args:
            collaboration_id = int(args["collaboration_id"])
            if not self.r.can_for_col(P.VIEW, collaboration_id):
                return {
                    "msg": "You lack the permission to view tasks "
                    f"from collaboration {collaboration_id}!"
                }, HTTPStatus.UNAUTHORIZED
            # dont join collaboration table if it is already joined
            has_already_joined_collab = False
            for visitor in visitors.iterate(q):
                if (
                    visitor.__visit_name__ == "table"
                    and visitor.name == "collaboration"
                ):
                    has_already_joined_collab = True
            if not has_already_joined_collab:
                q = q.join(db.Collaboration)
            q = q.filter(db.Collaboration.id == collaboration_id)

        if "init_org_id" in args:
            init_org_id = int(args["init_org_id"])
            if not self.r.allowed_for_org(P.VIEW, init_org_id):
                return {
                    "msg": "You lack the permission to view tasks "
                    f"from organization id={init_org_id}!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db.Task.init_org_id == init_org_id)

        if "init_user_id" in args:
            init_user_id = int(args["init_user_id"])
            init_user = db.User.get(init_user_id)
            if not init_user:
                return {
                    "msg": f"User id={init_user_id} does not exist!"
                }, HTTPStatus.BAD_REQUEST
            elif not self.r.allowed_for_org(P.VIEW, init_user.organization_id) and not (
                self.r.v_own.can() and g.user and init_user.id == g.user.id
            ):
                return {
                    "msg": "You lack the permission to view tasks "
                    f"from user id={init_user_id}!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db.Task.init_user_id == init_user_id)

        if "study_id" in args:
            study_id = int(args["study_id"])
            study = db.Study.get(study_id)
            if not study:
                return {
                    "msg": f"Study id={study_id} does not exist!"
                }, HTTPStatus.BAD_REQUEST
            elif not self.r.can_for_col(P.VIEW, study.collaboration_id):
                return {
                    "msg": "You lack the permission to view tasks "
                    f"from collaboration id={study.collaboration_id} that the study "
                    f"with id={study.id} belongs to!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db.Task.study_id == study_id)

        if "parent_id" in args:
            parent_id = int(args["parent_id"])
            parent = db.Task.get(parent_id)
            if not parent:
                return {
                    "msg": f"Parent task id={args['parent_id']} does not exist!"
                }, HTTPStatus.BAD_REQUEST
            elif not self.r.can_for_col(P.VIEW, parent.collaboration_id):
                return {
                    "msg": "You lack the permission to view tasks "
                    "from the collaboration that the task with parent_id="
                    f"{parent.collaboration_id} belongs to!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db.Task.parent_id == int(parent_id))

        if "job_id" in args:
            job_id = int(args["job_id"])
            task_in_job = g.session.scalars(
                select(db.Task).filter(db.Task.job_id == job_id)
            ).first()
            if not task_in_job:
                return {
                    "msg": f"Job id={args['job_id']} does not exist!"
                }, HTTPStatus.BAD_REQUEST
            elif not self.r.can_for_col(P.VIEW, task_in_job.collaboration_id):
                return {
                    "msg": "You lack the permission to view tasks "
                    "from the collaboration that the task with job_id="
                    f"{task_in_job.collaboration_id} belongs to!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db.Task.job_id == job_id)

        for param in ["name", "image", "description", "status"]:
            if param in args:
                q = q.filter(getattr(db.Task, param).like(args[param]))

        if "run_id" in args:
            run_id = int(args["run_id"])
            run = db.Run.get(run_id)
            if not run:
                return {
                    "msg": f"Run id={args['run_id']} does not exist!"
                }, HTTPStatus.BAD_REQUEST
            elif not self.r.can_for_col(P.VIEW, run.collaboration_id):
                return {
                    "msg": "You lack the permission to view tasks "
                    "from the collaboration that the run with id="
                    f"{run.collaboration_id} belongs to!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.join(db.Run).filter(db.Run.id == run_id)

        if "store_id" in args:
            store_id = int(args["store_id"])
            store = db.AlgorithmStore.get(store_id)
            if not store:
                return {
                    "msg": f"Algorithm store id={store_id} does not exist!"
                }, HTTPStatus.BAD_REQUEST
            q = q.filter(db.Task.algorithmstore_id == store_id)

        if "session_id" in args:
            session_id = int(args["session_id"])
            q = q.filter(db.Task.session_id == session_id)

        if "dataframe_id" in args:
            dataframe_id = args["dataframe_id"]
            q = q.filter(db.Task.dataframe_id == dataframe_id)

        if "database" in args:
            q = q.join(db.TaskDatabase).filter(
                db.TaskDatabase.database == args["database"]
            )

        if "is_user_created" in args:
            try:
                user_created = int(args["is_user_created"])
                if user_created == 0:
                    q = q.filter(db.Task.parent_id.isnot(None))
                else:
                    q = q.filter(db.Task.parent_id.is_(None))
            except ValueError:
                return {
                    "msg": (
                        "Invalid value for 'is_user_created' provided: "
                        f"'{args['is_user_created']}'. Should be an integer."
                    )
                }, HTTPStatus.BAD_REQUEST

        # order to get latest task first
        q = q.order_by(desc(db.Task.id))

        # paginate tasks
        try:
            page = Pagination.from_query(q, request, db.Task)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        # serialization schema
        schema = self._select_schema()

        return self.response(page, schema)

    @only_for(("user", "container"))
    def post(self):
        """Adds new computation task
        ---
        description: >-
          Creates a new task within a collaboration. If no `organization_ids`
          are given the task is send to all organizations within the
          collaboration. The endpoint can be accessed by both a `User` and
          `Container`.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Task|Global|Create|❌|❌|Create a new task|\n
          |Task|Collaboration|Create|❌|✅|Create a new task for a specific
          collaboration in which your organization participates|\n

          ## Accessed as `User`\n
          This endpoint is accessible to users. A new `job_id` is
          created when a user creates a task. The user needs to be within an
          organization that is part of the collaboration to which the task is
          posted.\n

          ## Accessed as `Container`\n
          When this endpoint is accessed by an algorithm container, it is considered to
          be a child-task of the container, and will get the `job_id` from the initial
          task. Containers have limited permissions to create tasks: for instance, they
          are only allowed to create tasks in the same collaboration.\n

        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'

        responses:
          200:
            description: Ok
          400:
            description: Wrong input, or not all required nodes are registered, or you
              are not in the collaboration yourself
          401:
            description: Unauthorized
          403:
            description: Algorithm store is not part of the collaboration
          404:
            description: Collaboration, session or study not found

        security:
          - bearerAuth: []

        tags: ["Task"]
        """
        data = request.get_json(silent=True)
        return self.post_task(
            data,
            self.r,
            should_be_compute=True,
        )


class Task(TaskBase):
    """Resource for /api/task"""

    @only_for(("user", "node", "container"))
    def get(self, id):
        """Get task
        ---
        description: >-
          Returns the task specified by the id.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Task|Global|View|❌|❌|View any task|\n
          |Task|Collaboration|View|✅|✅|View any task in your collaborations|
          |Task|Organization|View|❌|❌|View any task that your organization
          created|\n
          |Task|Own|View|❌|❌|View any task that you created|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Task id
            required: true
          - in: query
            name: include
            schema:
              type: string
            description: Include 'results' to include the task's results,
              'runs' to include details on algorithm runs. For including
              multiple, do either `include=x,y` or `include=x&include=y`.

        responses:
          200:
            description: Ok
          404:
            description: Task not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Task"]
        """
        task = db.Task.get(id)
        if not task:
            return {"msg": f"task id={id} is not found"}, HTTPStatus.NOT_FOUND

        # obtain schema
        schema = self._select_schema()

        # check permissions
        if not self.r.allowed_for_org(P.VIEW, task.init_org_id) and not (
            self.r.v_own.can() and g.user and task.init_user_id == g.user.id
        ):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED
        # if results are included, check permissions for results
        if (
            self.is_included("results")
            and not self.r_run.allowed_for_org(P.VIEW, task.init_org_id)
            and not (self.r.v_own.can() and g.user and task.init_user_id == g.user.id)
        ):
            return {
                "msg": "You lack the permission to view results for this task!"
            }, HTTPStatus.UNAUTHORIZED

        return schema.dump(task, many=False), HTTPStatus.OK

    @with_user
    def delete(self, id):
        """Remove task
        ---
        description: >-
          Remove tasks and their runs.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Task|Global|Delete|❌|❌|Delete a task|\n
          |Task|Collaboration|Delete|❌|❌|Delete a task from a collaboration
          in which your organization participates|\n
          |Task|Organization|Delete|❌|❌|Delete a task that your organization
          initiated|\n
          |Task|Own|Delete|❌|❌|Delete a task you created yourself|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Task id
            required: true

        responses:
          200:
            description: Ok
          404:
            description: Task not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Task"]
        """

        task = db.Task.get(id)
        if not task:
            return {"msg": f"Task id={id} not found"}, HTTPStatus.NOT_FOUND

        # validate permissions
        if not self.r.allowed_for_org(P.DELETE, task.init_org_id) and not (
            self.r.d_own.can() and task.init_user_id == g.user.id
        ):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # kill the task if it is still running
        if not TaskStatus.has_finished(task.status):
            kill_task(task, self.socketio)

        # retrieve runs that belong to this task
        log.info(f"Removing task id={task.id}")
        for run in task.runs:
            log.info(f" Removing run id={run.id}")
            run.delete()

        # delete child/grandchild/... tasks
        Task._delete_subtasks(task)

        # permissions ok, delete...
        task.delete()

        return {
            "msg": f"task id={id} and its algorithm run data have been "
            "successfully deleted"
        }, HTTPStatus.OK

    @staticmethod
    def _delete_subtasks(task: db.Task) -> None:
        """
        Delete subtasks recursively.

        Parameters
        ----------
        task : db.Task
            Task to delete.
        """
        for child_task in task.children:
            Task._delete_subtasks(child_task)
            log.info(f" Removing child task id={child_task.id}")
            child_task.delete()


class TaskStatusEndpoint(TaskBase):
    """Resource for /api/task/<id>/status"""

    @only_for(("user", "container"))
    def get(self, task_id: int):
        """Get task status
        ---
        description: >-
          Returns the status of the task specified by the id.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Task|Global|View|❌|❌|View any task|\n
          |Task|Collaboration|View|✅|✅|View any task in your collaborations|
          |Task|Organization|View|❌|❌|View any task that your organization
          created|\n
          |Task|Own|View|❌|❌|View any task that you created|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Task id
            required: true

        responses:
          200:
            description: Ok
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    status:
                      type: string
                      description: The status of the task
          404:
            description: Task not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Task"]
        """
        task = db.Task.get(task_id)
        if not task:
            log.error(f"Task with id={task_id} not found.")
            return {"msg": f"Task id={task_id} not found"}, HTTPStatus.NOT_FOUND

        if not self._has_permission_to_view_task(task):
            log.error(f"Unauthorized access to task id={task_id}.")
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        log.info(f"Returning status for task id={task_id}: {task.status}")
        return {"status": task.status}, HTTPStatus.OK

    def _has_permission_to_view_task(self, task: db.Task) -> bool:
        """
        Check if the user has permission to view the task.

        Parameters
        ----------
        task : db.Task
            Task to check permissions for.

        Returns
        -------
        bool
            True if the user has permission, False otherwise.
        """
        return self.r.allowed_for_org(P.VIEW, task.init_org_id) or (
            self.r.v_own.can() and g.user and task.init_user_id == g.user.id
        )
