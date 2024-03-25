import logging
import json

from flask import g, request, url_for
from flask_restful import Api
from flask_socketio import SocketIO
from http import HTTPStatus
from sqlalchemy import desc
from sqlalchemy.sql import visitors

from vantage6.common.globals import STRING_ENCODING
from vantage6.common.task_status import TaskStatus, has_task_finished
from vantage6.common.encryption import DummyCryptor
from vantage6.server import db
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
        q = g.session.query(db.Task)
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
            # FIXME refactor this after moving to SQLAlchemy 2.0
            has_already_joined_collab = False
            for visitor in visitors.iterate(q.statement):
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
            task_in_job = (
                q.session.query(db.Task).filter(db.Task.job_id == job_id).first()
            )
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
          When this endpoint is accessed by an algorithm container, it is
          considered to be a child-task of the container, and will get the
          `job_id` from the initial task. Containers have limited permissions
          to create tasks: they are only allowed to create tasks in the same
          collaboration using the same image.\n

        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'

        responses:
          200:
            description: Ok
          400:
            description: Supplied organizations are not in the supplied
              collaboration, or not all required nodes are registered, or you
              are not in the collaboration yourself
          401:
            description: Unauthorized
          404:
            description: Collaboration with `collaboration_id` not found

        security:
          - bearerAuth: []

        tags: ["Task"]
        """
        return self.post_task(request.get_json(), self.socketio, self.r)

    # TODO this function should be refactored to make it more readable
    @staticmethod
    def post_task(data: dict, socketio: SocketIO, rules: RuleCollection):
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
        """
        # validate request body
        errors = task_input_schema.validate(data)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        # A task can be created for a collaboration or a study. If it is for a study,
        # a study_id is always given, and a collaboration_id is optional. If it is for
        # a collaboration, a collaboration_id is always given, and a study_id is
        # never set. The following logic checks if the given study_id and
        # collaboration_id are valid and when both are provided, checks if they match.
        collaboration_id = data.get("collaboration_id")
        study_id = data.get("study_id")
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
        nodes = (
            g.session.query(db.Node)
            .filter(db.Node.organization_id.in_(org_ids))
            .filter(db.Node.collaboration_id == collaboration_id)
            .all()
        )
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
            image=image,
            init_org=init_org,
        )

        # create job_id. Users can only create top-level -tasks (they will not
        # have sub-tasks). Therefore, always create a new job_id. Tasks created
        # by containers are always sub-tasks
        if g.user:
            task.job_id = task.next_job_id()
            task.init_user_id = g.user.id
            log.debug(f"New job_id {task.job_id}")
        elif g.container:
            task.parent_id = g.container["task_id"]
            parent = db.Task.get(g.container["task_id"])
            task.job_id = parent.job_id
            task.init_user_id = parent.init_user_id
            log.debug(f"Sub task from parent_id={task.parent_id}")

        # save the databases that the task uses
        databases = data.get("databases")
        if isinstance(databases, str):
            databases = [{"label": databases}]
        elif databases is None:
            databases = []
        db_records = []
        for database in databases:
            if "label" not in database:
                return {
                    "msg": "Database label missing! The dictionary "
                    f"{database} should contain a 'label' key"
                }, HTTPStatus.BAD_REQUEST
            # remove label from the database dictionary, which apart from it
            # may only contain some optional parameters . Save optional
            # parameters as JSON without spaces to database
            label = database.pop("label")
            # TODO task.id is only set here because in between creating the
            # task and using the ID here, there are other database operations
            # that silently update the task.id (i.e. next_job_id() and
            # db.Task.get()). Task.id should be updated explicitly instead.
            db_records.append(
                db.TaskDatabase(
                    task_id=task.id,
                    database=label,
                    parameters=json.dumps(database, separators=(",", ":")),
                )
            )

        # All checks completed, save task to database
        task.save()
        [db_record.save() for db_record in db_records]  # pylint: disable=W0106

        # send socket event that task has been created
        socketio.emit(
            "task_created",
            {
                "task_id": task.id,
                "job_id": task.job_id,
                "collaboration_id": collaboration_id,
                "init_org_id": init_org.id,
            },
            room=f"collaboration_{collaboration_id}",
            namespace="/tasks",
        )

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
                status=TaskStatus.PENDING,
            )
            run.save()

        # notify nodes a new task available (only to online nodes), nodes that
        # are offline will receive this task on sign in.
        socketio.emit(
            "new_task",
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

        return task_schema.dump(task, many=False), HTTPStatus.CREATED

    @staticmethod
    def __verify_container_permissions(container, image, collaboration_id):
        """Validates that the container is allowed to create the task."""

        # check that the image is allowed: algorithm containers can only
        # create tasks with the same image
        if not image.endswith(container["image"]):
            log.warning(
                (
                    f"Container from node={container['node_id']} "
                    f"attempts to post a task using illegal image!?"
                )
            )
            log.warning(f"  task image: {image}")
            log.warning(f"  container image: {container['image']}")
            return False

        # check that parent task is not completed yet
        if has_task_finished(db.Task.get(container["task_id"]).status):
            log.warning(
                f"Container from node={container['node_id']} "
                f"attempts to start sub-task for a completed "
                f"task={container['task_id']}"
            )
            return False

        # check that node id is indeed part of the collaboration
        if not container["collaboration_id"] == collaboration_id:
            log.warning(
                f"Container attempts to create a task outside "
                f"collaboration_id={container['collaboration_id']} in "
                f"collaboration_id={collaboration_id}!"
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
            if config_option.key == "allowed_users":
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
        if not has_task_finished(task.status):
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
