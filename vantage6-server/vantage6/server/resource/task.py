import logging
import json
import datetime

from flask import g, request, url_for
from flask_restful import Api
from flask_socketio import SocketIO
from marshmallow import ValidationError
from http import HTTPStatus
from sqlalchemy import desc, select
from sqlalchemy.sql import visitors

from vantage6.common.globals import STRING_ENCODING, NodePolicy
from vantage6.common.enum import RunStatus, AlgorithmStepType, TaskDatabaseType
from vantage6.common.encryption import DummyCryptor
from vantage6.backend.common import get_server_url
from vantage6.server import db
from vantage6.server.algo_store_communication import request_algo_store
from vantage6.server.permission import (
    RuleCollection,
    Scope as S,
    PermissionManager,
    Operation as P,
)
from vantage6.server.resource import only_for, ServicesResources, with_user
from vantage6.server.resource.common.output_schema import (
    TaskSchema,
    TaskWithResultSchema,
    TaskWithRunSchema,
    TaskWithRunAndResultSchema,
)
from vantage6.server.resource.common.input_schema import TaskInputSchema
from vantage6.backend.common.resource.pagination import Pagination
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

task_input_schema = TaskInputSchema()


class TaskBase(ServicesResources):
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
            if not self.r.can_for_org(P.VIEW, init_org_id):
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
                    "msg": f"User id={init_user_id} does not " "exist!"
                }, HTTPStatus.BAD_REQUEST
            elif not self.r.can_for_org(P.VIEW, init_user.organization_id) and not (
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
                    "msg": f'Parent task id={args["parent_id"]} does not ' "exist!"
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
                    "msg": f'Job id={args["job_id"]} does not exist!'
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
                    "msg": f'Run id={args["run_id"]} does not exist!'
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
          task. Containers have limited permissions to create tasks: they are only
          allowed to create tasks in the same collaboration and in case the
          collaboration option 'session_restrict_to_same_image' is set to True, it
          the same image as the parent task has to be used.\n

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
        try:
            request.get_json()
        except Exception:
            return {"msg": "Request body is incorrect"}, HTTPStatus.BAD_REQUEST
        return self.post_task(
            request.get_json(),
            self.socketio,
            self.r,
            self.config,
            AlgorithmStepType.COMPUTE,
        )

    # TODO this function should be refactored to make it more readable
    @staticmethod
    def post_task(
        data: dict,
        socketio: SocketIO,
        rules: RuleCollection,
        config: dict,
        action: AlgorithmStepType,
    ):
        """
        Create new task and algorithm runs. Send the task to the nodes.

        Parameters
        ----------
        data : dict
            Task data
        socketio : SocketIO
            SocketIO server instance
        rules : RuleCollection
            Rule collection instance
        config : dict
            Configuration dictionary
        action : AlgorithmStepType
            Action to performed by the task
        """
        # validate request body
        try:
            data = task_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # A task always belongs to a session
        session_id = data["session_id"]
        session: db.Session = db.Session.get(session_id)
        if not session:
            return {"msg": f"Session id={session_id} not found!"}, HTTPStatus.NOT_FOUND

        # A task can be created for a collaboration or a study. If it is for a study,
        # a study_id is always given, and a collaboration_id is optional. If it is for
        # a collaboration, a collaboration_id is always given, and a study_id is
        # never set. The following logic checks if the given study_id and
        # collaboration_id are valid and when both are provided, checks if they match.
        collaboration_id = data.get("collaboration_id")
        study_id = data.get("study_id")

        if not collaboration_id and not study_id:
            return {
                "msg": "Either a collaboration_id or a study_id should be provided!"
            }, HTTPStatus.BAD_REQUEST

        study = None
        if collaboration_id:
            collaboration = db.Collaboration.get(collaboration_id)
            if not collaboration:
                return {
                    "msg": f"Collaboration id={collaboration_id} not found!"
                }, HTTPStatus.NOT_FOUND
        if study_id:
            study = db.Study.get(study_id)
            if not study:
                return {"msg": f"Study id={study_id} not found"}, HTTPStatus.NOT_FOUND

            # check if collaboration and study match if both are set
            if collaboration_id and study.collaboration_id != collaboration_id:
                return {
                    "msg": (
                        f"The study_id '{study.id}' does not belong to the "
                        f"collaboration_id '{collaboration_id}' that is given."
                    )
                }, HTTPStatus.BAD_REQUEST

            # get the collaboration object as well
            collaboration_id = study.collaboration_id
            collaboration = db.Collaboration.get(collaboration_id)

        organizations_json_list = data.get("organizations")
        org_ids = [org.get("id") for org in organizations_json_list]
        db_ids = collaboration.get_organization_ids()

        # Check that all organization ids are within the collaboration, this
        # also ensures us that the organizations exist
        if not set(org_ids).issubset(db_ids):
            return {
                "msg": (
                    "At least one of the supplied organizations in not within "
                    "the collaboration."
                )
            }, HTTPStatus.BAD_REQUEST
        # check that they are within the study (if that has been defined)
        if study:
            study_org_ids = [org.id for org in study.organizations]
            if not set(org_ids).issubset(study_org_ids):
                return {
                    "msg": (
                        "At least one of the supplied organizations in not within "
                        "the specified study."
                    )
                }, HTTPStatus.BAD_REQUEST

        # check if all the organizations have a registered node
        nodes = g.session.scalars(
            select(db.Node)
            .filter(db.Node.organization_id.in_(org_ids))
            .filter(db.Node.collaboration_id == collaboration_id)
        ).all()
        if len(nodes) < len(org_ids):
            present_nodes = [node.organization_id for node in nodes]
            missing = [str(id) for id in org_ids if id not in present_nodes]
            return {
                "msg": (
                    "Cannot create this task because there are no nodes registered"
                    f" for the following organization(s): {', '.join(missing)}."
                )
            }, HTTPStatus.BAD_REQUEST
        # check if any of the nodes that are offline shared their configuration
        # info and if this prevents this user from creating this task
        if g.user:
            for node in nodes:
                if Tasks._node_doesnt_allow_user_task(node.config):
                    return {
                        "msg": (
                            "Cannot create this task because one of the nodes that"
                            " you are trying to send this task to does not allow "
                            "you to create tasks."
                        )
                    }, HTTPStatus.BAD_REQUEST

        # figure out the initiating organization of the task
        if g.user:
            init_org = g.user.organization
        else:  # g.container:
            init_org = db.Node.get(g.container["node_id"]).organization

        # check if the initiating organization is part of the collaboration
        if init_org not in collaboration.organizations:
            return {
                "msg": "You can only create tasks for collaborations "
                "you are participating in!"
            }, HTTPStatus.UNAUTHORIZED

        # verify permissions
        image = data.get("image", "")
        if g.user and not rules.can_for_col(P.CREATE, collaboration.id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        elif g.container:
            # verify that the container has permissions to create the task
            if not Tasks.__verify_container_permissions(
                g.container, image, collaboration_id
            ):
                return {"msg": "Container-token is not valid"}, HTTPStatus.UNAUTHORIZED

        # get the algorithm store
        if g.user:
            store_id = data.get("store_id")
            store = None
            if store_id:
                store = db.AlgorithmStore.get(store_id)
                if not store:
                    return {
                        "msg": f"Algorithm store id={store_id} not found!"
                    }, HTTPStatus.BAD_REQUEST
                # check if the store is part of the collaboration
                if (
                    not store.is_for_all_collaborations()
                    and store.collaboration_id != collaboration_id
                ):
                    return {
                        "msg": (
                            "The algorithm store is not part of the collaboration "
                            "to which the task is posted."
                        )
                    }, HTTPStatus.FORBIDDEN
                # get the algorithm from the algorithm store
                try:
                    image, digest = Tasks._get_image_and_hash_from_store(
                        store=store,
                        image=image,
                        config=config,
                        server_url_from_request=data.get("server_url"),
                    )
                except Exception as e:
                    log.exception("Error while getting image from store: %s", e)
                    return {"msg": str(e)}, HTTPStatus.BAD_REQUEST

                if digest:
                    image_with_hash = f"{image}@{digest}"
                else:
                    # hash lookup in store was unsuccessful, use image without hash, but
                    # also set store to None as it was not successfully looked up
                    image_with_hash = image
                    store = None
            else:
                # no need to determine hash if we don't look it up in a store
                image_with_hash = image
        else:  # ( we are dealing with g.container)
            parent = db.Task.get(g.container["task_id"])
            store = parent.algorithm_store
            image_with_hash = parent.image

        # Obtain the user requested database or dataframes
        databases = data.get("databases", [])

        # A task can be dependent on one or more other task(s). There are three cases:
        #
        # 1. When a dataframe modification task is created (data extraction or
        #    preprocessing) the next modification task should be dependent on the
        #    previous modification task. This is to prevent that the dataframe is
        #    modified by two tasks at the same time.
        # 2. When a dataframe modification task is created, the task should be dependent
        #    on the compute task(s) that are currently computing the dataframe. This is
        #    to prevent that the dataframe is modified during the computation.
        # 3. When a compute task is created, the task should be dependent on the
        #    modification task(s) that are currently modifying the dataframe. This is
        #    to prevent that the dataframe is modified during the computation.
        #
        # Thus when a modification task is running, all new compute tasks and all new
        # modification tasks will be depending on it. When a compute task is running,
        # all new modification tasks will depend on it. The `depends_on_ids` parameter
        # is set by the session endpoints.
        dependent_tasks = []
        for database in databases:
            for key in ["label", "type"]:
                if key not in database:
                    return {
                        "msg": f"Database {key} missing! The dictionary "
                        f"{database} should contain a '{key}' key"
                    }, HTTPStatus.BAD_REQUEST

            # add last modification task to dependent tasks
            if database["type"] == TaskDatabaseType.DATAFRAME:
                df = db.Dataframe.select(session, database["label"])
                if not df:
                    return {
                        "msg": f"Dataframe '{database['label']}' not found!"
                    }, HTTPStatus.NOT_FOUND

                if not df.ready:
                    dependent_tasks.append(df.last_session_task)

        # These `depends_on_ids` are the task ids supplied by the session endpoints.
        # However they can also be user defined, although this has no use case yet.
        dependent_task_ids = data.get("depends_on_ids", [])
        for dependent_task_id in dependent_task_ids:

            dependent_task = db.Task.get(dependent_task_id)

            if not dependent_task:
                return {
                    "msg": f"Task with id={dependent_task_id} not found!"
                }, HTTPStatus.NOT_FOUND

            if dependent_task.session_id != session_id:
                return {
                    "msg": (
                        "The task you are trying to depend on is not part of the "
                        "same session."
                    )
                }, HTTPStatus.BAD_REQUEST

            dependent_tasks.append(dependent_task)

        # Filter that we did not end up with duplicates because of various conditions
        dependent_tasks = list(set(dependent_tasks))

        # check that the input is valid. If the collaboration is encrypted, it
        # should not be possible to read the input, and we should not save it
        # to the database as it may be sensitive information. Vice versa, if
        # the collaboration is not encrypted, we should not allow the user to
        # send encrypted input.
        is_valid_input, error_msg = Tasks._check_input_encryption(
            organizations_json_list, collaboration
        )
        if not is_valid_input:
            return {"msg": error_msg}, HTTPStatus.BAD_REQUEST

        # permissions ok, create task record and TaskDatabase records
        task = db.Task(
            collaboration=collaboration,
            study=study,
            name=data.get("name", ""),
            description=data.get("description", ""),
            image=image_with_hash,
            init_org=init_org,
            algorithm_store=store,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            session=session,
            depends_on=dependent_tasks,
            dataframe_id=data.get("dataframe_id"),
        )
        task.save()

        # create job_id. Users can only create top-level -tasks (they will not
        # have sub-tasks). Therefore, always create a new job_id. Tasks created
        # by containers are always sub-tasks
        if g.user:
            task.job_id = task.next_job_id()
            task.init_user_id = g.user.id
            log.debug(f"New job_id {task.job_id}")
        elif g.container:
            task.parent_id = g.container["task_id"]
            # save task after changing it before using session to get another task
            task.save()
            parent = db.Task.get(g.container["task_id"])
            task.job_id = parent.job_id
            task.init_user_id = parent.init_user_id
            log.debug(f"Sub task from parent_id={task.parent_id}")

        # save the databases that the task uses
        for database in databases:

            # TODO task.id is only set here because in between creating the
            # task and using the ID here, there are other database operations
            # that silently update the task.id (i.e. next_job_id() and
            # db.Task.get()). Task.id should be updated explicitly instead.
            task_db = db.TaskDatabase(
                task_id=task.id,
                label=database["label"],
                type_=database["type"],
            )
            task_db.save()

        # All checks completed, save task to database
        task.save()

        # now we need to create results for the nodes to fill. Each node
        # receives their instructions from a result, not from the task itself
        log.debug(f"Assigning task to {len(organizations_json_list)} nodes.")
        for org in organizations_json_list:
            organization = db.Organization.get(org["id"])
            log.debug(f"Assigning task to '{organization.name}'.")
            input_ = org.get("input")
            # FIXME: legacy input from the client, could be removed at some
            # point
            if isinstance(input_, dict):
                input_ = json.dumps(input_).encode(STRING_ENCODING)
            # Create run
            run = db.Run(
                task=task,
                organization=organization,
                input=input_,
                status=RunStatus.PENDING,
                action=action,
            )
            run.save()

        # notify nodes a new task available (only to online nodes), nodes that
        # are offline will receive this task on sign in.
        socketio.emit(
            "new_task_update",
            {"id": task.id, "parent_id": task.parent_id},
            namespace="/tasks",
            room=f"collaboration_{task.collaboration_id}",
        )

        # add some logging
        log.info(f"New task for collaboration '{task.collaboration.name}'")
        if g.user:
            log.debug(f" created by: '{g.user.username}'")
        else:
            log.debug(
                f" created by container on node_id="
                f"{g.container['node_id']}"
                f" for (parent) task_id={g.container['task_id']}"
            )

        log.debug(f" url: '{url_for('task_with_id', id=task.id)}'")
        log.debug(f" name: '{task.name}'")
        log.debug(f" image: '{task.image}'")
        log.debug(f" session ID: '{task.session_id}'")

        return task_schema.dump(task, many=False), HTTPStatus.CREATED

    @staticmethod
    def __verify_container_permissions(container, image, collaboration_id):
        """Validates that the container is allowed to create the task."""

        # check that node id is indeed part of the collaboration
        if not container["collaboration_id"] == collaboration_id:
            log.warning(
                f"Container attempts to create a task outside "
                f"collaboration_id={container['collaboration_id']} in "
                f"collaboration_id={collaboration_id}!"
            )
            return False

        # check that the image is allowed: algorithm containers can only
        # create tasks with the same image
        collaboration: db.Collaboration = db.Collaboration.get(collaboration_id)
        if collaboration.session_restrict_to_same_image:
            if not image != container["image"]:
                log.warning(
                    "Container from node=%s attempts to post a "
                    "task using a different image than the parent task. That is not "
                    "allowed in this collaboration.",
                    container["node_id"],
                )
                log.warning("  requested image: %s", image)
                log.warning("  parent image: %s", container["image"])
                return False

        # check that parent task is not completed yet
        if RunStatus.has_finished(db.Task.get(container["task_id"]).status):
            log.warning(
                "Container from node=%s attempts to start sub-task for a completed "
                "task=%s",
                container["node_id"],
                container["task_id"],
            )
            return False

        return True

    @staticmethod
    def _node_doesnt_allow_user_task(node_configs: list[db.NodeConfig]) -> bool:
        """
        Checks if the node allows user to create task.

        Parameters
        ----------
        node_configs : list[db.NodeConfig]
            List of node configurations.

        Returns
        -------
        bool
            True if the node doesn't allow the user to create task.
        """
        has_limitations = False
        for config_option in node_configs:
            if config_option.key == NodePolicy.ALLOWED_USERS:
                has_limitations = True
                # TODO expand when we allow also usernames, like orgs below
                if g.user.id == int(config_option.value):
                    return False
            elif config_option.key == "allowed_orgs":
                has_limitations = True
                if config_option.value.isdigit():
                    if g.user.organization_id == int(config_option.value):
                        return False
                else:
                    org = db.Organization.get_by_name(config_option.value)
                    if org and g.user.organization_id == org.id:
                        return False
        return has_limitations

    @staticmethod
    def _check_input_encryption(
        organizations_json_list: list[dict], collaboration: db.Collaboration
    ) -> tuple[bool, str]:
        """
        Check if the input encryption status matches the expected status for
        the collaboration. Also, check that if the input is not encrypted, it
        can be read as a string.

        Parameters
        ----------
        organizations_json_list : list[dict]
            List of organizations which contains the input per organization.
        collaboration : db.Collaboration
            Collaboration object.

        Returns
        -------
        bool
            True if the input is encrypted.
        str
            Error message if the input is valid.
        """
        dummy_cryptor = DummyCryptor()
        for org in organizations_json_list:
            input_ = org.get("input")
            decrypted_input = dummy_cryptor.decrypt_str_to_bytes(input_)
            is_input_readable = False
            try:
                decrypted_input.decode(STRING_ENCODING)
                is_input_readable = True
            except UnicodeDecodeError:
                pass

            if collaboration.encrypted and is_input_readable:
                return (
                    False,
                    (
                        "Your collaboration requires encryption, but input is not "
                        "encrypted! Please encrypt your input before sending it."
                    ),
                )
            elif not collaboration.encrypted and not is_input_readable:
                return False, (
                    "Your task's input cannot be parsed. Your input should be "
                    "a base64 encoded JSON string. Note that if you are using "
                    "the user interface or Python client, this should be done "
                    "for you. Also, make sure not to encrypt your input, "
                    "as your collaboration is set to not use encryption."
                )
        return True, ""

    @staticmethod
    def _get_image_and_hash_from_store(
        store: db.AlgorithmStore,
        image: str,
        config: dict,
        server_url_from_request: str | None = None,
    ) -> tuple[str, str]:
        """
        Determine the image and hash from the algorithm store.

        Parameters
        ----------
        store : db.AlgorithmStore
            Algorithm store.
        image : str
            URL of the docker image to be used.
        config : dict
            Configuration dictionary.
        server_url_from_request : str, optional
            Server URL from the request, by default None

        Returns
        -------
        tuple[str, str]
            Image url and image hash digest.

        Raises
        ------
        Exception
            If the algorithm cannot be retrieved from the store.
        """
        server_url = get_server_url(config, server_url_from_request)
        if not server_url:
            raise ValueError(
                "Server URL is not set in the configuration nor in the request "
                "arguments. Please provide it as 'server_url' in the request."
            )
        # get the algorithm from the store
        response, status_code = request_algo_store(
            algo_store_url=store.url,
            server_url=server_url,
            endpoint="algorithm",
            method="GET",
            params={"image": image},
        )
        if status_code != HTTPStatus.OK:
            raise Exception(
                f"Could not retrieve algorithm from store! {response.get('msg')}"
            )
        try:
            algorithm = response.json()["data"][0]
        except Exception as e:
            raise Exception("Algorithm not found in store!") from e

        image = algorithm["image"]
        digest = algorithm["digest"]
        # TODO v5+ remove this check? The digest should always be present for an
        # algorithm from stores started in v4.6 and higher
        if image and not digest:
            log.warning(
                "Algorithm image %s does not have a digest in the algorithm store. Will"
                " use it without digest.",
                image,
            )
            return image, None
        return image, digest


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
        if not self.r.can_for_org(P.VIEW, task.init_org_id) and not (
            self.r.v_own.can() and g.user and task.init_user_id == g.user.id
        ):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED
        # if results are included, check permissions for results
        if (
            self.is_included("results")
            and not self.r_run.can_for_org(P.VIEW, task.init_org_id)
            and not (self.r.v_own.can() and g.user and task.init_user_id == g.user.id)
        ):
            return {
                "msg": "You lack the permission to view results for this " "task!"
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
        if not self.r.can_for_org(P.DELETE, task.init_org_id) and not (
            self.r.d_own.can() and task.init_user_id == g.user.id
        ):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # kill the task if it is still running
        if not RunStatus.has_finished(task.status):
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
