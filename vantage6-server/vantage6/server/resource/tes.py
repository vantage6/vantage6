import logging
import json
import datetime

from flask import g, request
from flask_restful import Api
from flask_socketio import SocketIO
from http import HTTPStatus
from sqlalchemy import desc

from vantage6.common import bytes_to_base64s
from vantage6.common.globals import STRING_ENCODING
from vantage6.common.serialization import serialize
from vantage6.common.task_status import TaskStatus, has_task_finished
from vantage6.server import db
from vantage6.server.permission import (
    RuleCollection,
    Scope as S,
    PermissionManager,
    Operation as P,
)
from vantage6.server.resource import only_for, ServicesResources, with_user
from vantage6.server.resource.task import Tasks as TasksResource
from vantage6.server.resource.event import kill_task
from vantage6.server.resource.common.tes_schema import (
    TesTaskInputSchema,
    TesTaskSchema,
    TesListTasksResponseSchema,
    TesCreateTaskResponseSchema,
    TesCancelTaskResponseSchema,
    TesServiceInfoSchema,
)

module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)

TES_API_VERSION = "1.1.0"
TES_BASE_PATH = "/ga4gh/tes/v1"


VANTAGE6_TO_TES_STATE = {
    TaskStatus.PENDING: "QUEUED",
    TaskStatus.INITIALIZING: "INITIALIZING",
    TaskStatus.ACTIVE: "RUNNING",
    TaskStatus.COMPLETED: "COMPLETE",
    TaskStatus.FAILED: "EXECUTOR_ERROR",
    TaskStatus.START_FAILED: "SYSTEM_ERROR",
    TaskStatus.NO_DOCKER_IMAGE: "SYSTEM_ERROR",
    TaskStatus.CRASHED: "EXECUTOR_ERROR",
    TaskStatus.KILLED: "CANCELED",
    TaskStatus.NOT_ALLOWED: "SYSTEM_ERROR",
    TaskStatus.UNKNOWN_ERROR: "SYSTEM_ERROR",
}

TES_TO_VANTAGE6_STATE = {
    "UNKNOWN": None,
    "QUEUED": TaskStatus.PENDING,
    "INITIALIZING": TaskStatus.INITIALIZING,
    "RUNNING": TaskStatus.ACTIVE,
    "PAUSED": TaskStatus.ACTIVE,
    "COMPLETE": TaskStatus.COMPLETED,
    "EXECUTOR_ERROR": TaskStatus.CRASHED,
    "SYSTEM_ERROR": TaskStatus.FAILED,
    "CANCELED": TaskStatus.KILLED,
    "CANCELING": TaskStatus.ACTIVE,
    "PREEMPTED": TaskStatus.FAILED,
}


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the TES (Task Execution Service) resource.

    Parameters
    ----------
    api : Api
        Flask restful api instance
    api_base : str
        Base url of the api (not used, TES has its own base path)
    services : dict
        Dictionary with services required for the resource endpoints
    """
    log.info(f'Setting up "{TES_BASE_PATH}" and subdirectories')

    api.add_resource(
        TesServiceInfo,
        TES_BASE_PATH + "/service-info",
        endpoint="tes_service_info",
        methods=("GET",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        TesTasks,
        TES_BASE_PATH + "/tasks",
        endpoint="tes_tasks",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )

    api.add_resource(
        TesTask,
        TES_BASE_PATH + "/tasks/<string:id>",
        endpoint="tes_task",
        methods=("GET",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        TesCancelTask,
        TES_BASE_PATH + "/tasks/<string:id>:cancel",
        endpoint="tes_cancel_task",
        methods=("POST",),
        resource_class_kwargs=services,
    )


def permissions(permissions: PermissionManager) -> None:
    """
    Define the permissions for this resource.

    The TES resource reuses the task permissions, so no additional permissions
    are defined here.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """
    pass


tes_task_input_schema = TesTaskInputSchema()
tes_task_schema = TesTaskSchema()
tes_list_response_schema = TesListTasksResponseSchema()
tes_create_response_schema = TesCreateTaskResponseSchema()
tes_cancel_response_schema = TesCancelTaskResponseSchema()
tes_service_info_schema = TesServiceInfoSchema()


def vantage6_task_to_tes(
    task: db.Task, view: str = "MINIMAL"
) -> dict:
    """
    Convert a vantage6 Task to a TES task representation.

    Parameters
    ----------
    task : db.Task
        The vantage6 task to convert
    view : str
        The view level: MINIMAL, BASIC, or FULL

    Returns
    -------
    dict
        TES-formatted task
    """
    tes_state = VANTAGE6_TO_TES_STATE.get(task.status, "UNKNOWN")

    tes_task = {
        "id": str(task.id),
        "state": tes_state,
    }

    if view in ("BASIC", "FULL"):
        tes_task["name"] = task.name or ""
        tes_task["description"] = task.description or ""
        tes_task["creation_time"] = (
            task.created_at.isoformat() if task.created_at else None
        )

        executors = [
            {
                "image": task.image.split("@")[0] if task.image else "",
                "command": [],
            }
        ]
        tes_task["executors"] = executors

        tags = {
            "vantage6_collaboration_id": str(task.collaboration_id),
            "vantage6_job_id": str(task.job_id) if task.job_id else None,
        }
        if task.study_id:
            tags["vantage6_study_id"] = str(task.study_id)
        if task.init_org_id:
            tags["vantage6_init_org_id"] = str(task.init_org_id)
        tes_task["tags"] = tags

        inputs = []
        for run in task.runs:
            if run.input:
                inputs.append(
                    {
                        "name": f"input_org_{run.organization_id}",
                        "description": f"Input for organization {run.organization_id}",
                        "path": f"/vantage6/input/{run.organization_id}",
                        "content": run.input if isinstance(run.input, str) else None,
                    }
                )
        tes_task["inputs"] = inputs

        outputs = []
        for run in task.runs:
            if run.result:
                outputs.append(
                    {
                        "name": f"output_org_{run.organization_id}",
                        "description": f"Output for organization {run.organization_id}",
                        "path": f"/vantage6/output/{run.organization_id}",
                        "url": f"vantage6://run/{run.id}/result",
                    }
                )
        tes_task["outputs"] = outputs

    if view == "FULL":
        logs = []
        for run in task.runs:
            executor_logs = []
            exit_code = 0 if run.status == TaskStatus.COMPLETED else -1
            if has_task_finished(run.status) and run.status != TaskStatus.COMPLETED:
                exit_code = 1

            executor_log = {
                "exit_code": exit_code,
            }
            if run.started_at:
                executor_log["start_time"] = run.started_at.isoformat()
            if run.finished_at:
                executor_log["end_time"] = run.finished_at.isoformat()
            if run.log:
                executor_log["stderr"] = run.log

            executor_logs.append(executor_log)

            task_log = {
                "logs": executor_logs,
                "metadata": {
                    "organization_id": str(run.organization_id),
                    "run_id": str(run.id),
                },
            }
            if run.started_at:
                task_log["start_time"] = run.started_at.isoformat()
            if run.finished_at:
                task_log["end_time"] = run.finished_at.isoformat()

            output_file_logs = []
            if run.result:
                output_file_logs.append(
                    {
                        "url": f"vantage6://run/{run.id}/result",
                        "path": f"/vantage6/output/{run.organization_id}",
                    }
                )
            task_log["outputs"] = output_file_logs
            logs.append(task_log)

        tes_task["logs"] = logs

    return tes_task


class TesBase(ServicesResources):
    """Base class for TES resources."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, "task")

    def _get_view(self) -> str:
        """Get the view parameter from the request."""
        view = request.args.get("view", "MINIMAL").upper()
        if view not in ("MINIMAL", "BASIC", "FULL"):
            view = "MINIMAL"
        return view


class TesServiceInfo(TesBase):
    """Resource for GET /ga4gh/tes/v1/service-info"""

    @only_for(("user", "node", "container"))
    def get(self):
        """Get service information
        ---
        description: >-
          Returns information about the TES service implementation.

        responses:
          200:
            description: Service information

        security:
          - bearerAuth: []

        tags: ["TES"]
        """
        service_info = {
            "id": "vantage6-tes",
            "name": "vantage6 TES API",
            "type": {
                "group": "org.ga4gh",
                "artifact": "tes",
                "version": TES_API_VERSION,
            },
            "description": (
                "Task Execution Service API implementation for vantage6. "
                "This API provides GA4GH TES-compatible access to vantage6 tasks."
            ),
            "organization": {
                "name": "vantage6",
                "url": "https://vantage6.ai",
            },
            "version": TES_API_VERSION,
            "storage": [],
            "tesResources_backend_parameters": [
                "vantage6_collaboration_id",
                "vantage6_study_id",
                "vantage6_store_id",
            ],
        }

        return service_info, HTTPStatus.OK


class TesTasks(TesBase):
    """Resource for /ga4gh/tes/v1/tasks"""

    @only_for(("user", "node", "container"))
    def get(self):
        """List tasks
        ---
        description: >-
          List tasks. Returns a paginated list of tasks matching the query
          parameters.

        parameters:
          - in: query
            name: name_prefix
            schema:
              type: string
            description: Filter by task name prefix
          - in: query
            name: state
            schema:
              type: string
              enum: [UNKNOWN, QUEUED, INITIALIZING, RUNNING, PAUSED, COMPLETE,
                     EXECUTOR_ERROR, SYSTEM_ERROR, CANCELED, CANCELING, PREEMPTED]
            description: Filter by task state
          - in: query
            name: page_size
            schema:
              type: integer
            description: Number of tasks per page (default 256, max 2048)
          - in: query
            name: page_token
            schema:
              type: string
            description: Page token for pagination
          - in: query
            name: view
            schema:
              type: string
              enum: [MINIMAL, BASIC, FULL]
            description: Level of detail (default MINIMAL)
          - in: query
            name: tag_key
            schema:
              type: array
              items:
                type: string
            description: Filter by tag keys
          - in: query
            name: tag_value
            schema:
              type: array
              items:
                type: string
            description: Filter by tag values (companion to tag_key)

        responses:
          200:
            description: List of tasks
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["TES"]
        """
        args = request.args
        view = self._get_view()

        q = g.session.query(db.Task)
        auth_org_id = self.obtain_organization_id()

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

        if "name_prefix" in args:
            q = q.filter(db.Task.name.like(f"{args['name_prefix']}%"))

        state_filter = None
        if "state" in args:
            tes_state = args["state"].upper()
            state_filter = TES_TO_VANTAGE6_STATE.get(tes_state)

        tag_keys = args.getlist("tag_key")
        tag_values = args.getlist("tag_value")
        for key, value in zip(tag_keys, tag_values):
            if key == "vantage6_collaboration_id":
                q = q.filter(db.Task.collaboration_id == int(value))
            elif key == "vantage6_study_id":
                q = q.filter(db.Task.study_id == int(value))
            elif key == "vantage6_job_id":
                q = q.filter(db.Task.job_id == int(value))
            elif key == "vantage6_init_org_id":
                q = q.filter(db.Task.init_org_id == int(value))

        q = q.order_by(desc(db.Task.id))

        page_size = min(int(args.get("page_size", 256)), 2048)
        page_token = args.get("page_token")

        offset = 0
        if page_token:
            try:
                offset = int(page_token)
            except ValueError:
                offset = 0

        if state_filter:
            all_tasks = q.all()
            filtered_tasks = [
                t for t in all_tasks if t.status == state_filter.value
            ]
            tasks = filtered_tasks[offset : offset + page_size + 1]
        else:
            tasks = q.offset(offset).limit(page_size + 1).all()

        has_more = len(tasks) > page_size
        if has_more:
            tasks = tasks[:page_size]

        tes_tasks = [vantage6_task_to_tes(task, view) for task in tasks]

        response = {"tasks": tes_tasks}
        if has_more:
            response["next_page_token"] = str(offset + page_size)

        return response, HTTPStatus.OK

    @only_for(("user", "container"))
    def post(self):
        """Create a task
        ---
        description: >-
          Create a new task. The task will be queued for execution.

        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/tesTask'

        responses:
          200:
            description: Task created successfully
          400:
            description: Invalid request
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["TES"]
        """
        try:
            data = request.get_json()
        except Exception:
            return {"msg": "Request body is incorrect"}, HTTPStatus.BAD_REQUEST

        errors = tes_task_input_schema.validate(data)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        executors = data.get("executors", [])
        if not executors:
            return {
                "msg": "At least one executor is required"
            }, HTTPStatus.BAD_REQUEST

        image = executors[0].get("image")
        if not image:
            return {"msg": "Executor image is required"}, HTTPStatus.BAD_REQUEST

        tags = data.get("tags", {})
        collaboration_id = tags.get("vantage6_collaboration_id")
        study_id = tags.get("vantage6_study_id")
        store_id = tags.get("vantage6_store_id")

        resources = data.get("resources", {})
        backend_params = resources.get("backend_parameters", {})
        if not collaboration_id:
            collaboration_id = backend_params.get("vantage6_collaboration_id")
        if not study_id:
            study_id = backend_params.get("vantage6_study_id")
        if not store_id:
            store_id = backend_params.get("vantage6_store_id")

        if not collaboration_id and not study_id:
            return {
                "msg": (
                    "Either vantage6_collaboration_id or vantage6_study_id must be "
                    "provided in tags or resources.backend_parameters"
                )
            }, HTTPStatus.BAD_REQUEST

        organizations = []
        inputs = data.get("inputs", [])
        for inp in inputs:
            org_id = None
            name = inp.get("name", "")
            if name.startswith("input_org_"):
                try:
                    org_id = int(name.replace("input_org_", ""))
                except ValueError:
                    pass

            if not org_id:
                path = inp.get("path", "")
                if "/vantage6/input/" in path:
                    try:
                        org_id = int(path.split("/vantage6/input/")[-1].split("/")[0])
                    except (ValueError, IndexError):
                        pass

            if org_id:
                org_input = {
                    "id": org_id,
                }
                content = inp.get("content")
                if content:
                    org_input["input"] = content
                organizations.append(org_input)

        default_input = bytes_to_base64s(serialize({}))

        if not organizations:
            org_ids_str = backend_params.get("vantage6_organization_ids", "")
            if org_ids_str:
                try:
                    org_ids = [int(x.strip()) for x in org_ids_str.split(",")]
                    organizations = [
                        {"id": org_id, "input": default_input} for org_id in org_ids
                    ]
                except ValueError:
                    pass

        if not organizations:
            if collaboration_id:
                collaboration = db.Collaboration.get(int(collaboration_id))
                if collaboration:
                    organizations = [
                        {"id": org.id, "input": default_input}
                        for org in collaboration.organizations
                    ]

        if not organizations:
            return {
                "msg": (
                    "Could not determine target organizations. Provide inputs with "
                    "organization IDs or set vantage6_organization_ids in "
                    "resources.backend_parameters"
                )
            }, HTTPStatus.BAD_REQUEST

        databases = []
        db_labels = backend_params.get("vantage6_databases", "")
        if db_labels:
            databases = [{"label": label.strip()} for label in db_labels.split(",")]

        v6_task_data = {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "image": image,
            "organizations": organizations,
        }

        if collaboration_id:
            v6_task_data["collaboration_id"] = int(collaboration_id)
        if study_id:
            v6_task_data["study_id"] = int(study_id)
        if store_id:
            v6_task_data["store_id"] = int(store_id)
        if databases:
            v6_task_data["databases"] = databases

        result, status_code = TasksResource.post_task(
            v6_task_data, self.socketio, self.r, self.config
        )

        if status_code != HTTPStatus.CREATED:
            return result, status_code

        task_id = result.get("id")
        return {"id": str(task_id)}, HTTPStatus.OK


class TesTask(TesBase):
    """Resource for /ga4gh/tes/v1/tasks/<id>"""

    @only_for(("user", "node", "container"))
    def get(self, id: str):
        """Get a task
        ---
        description: >-
          Get a task by ID.

        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Task ID
          - in: query
            name: view
            schema:
              type: string
              enum: [MINIMAL, BASIC, FULL]
            description: Level of detail (default MINIMAL)

        responses:
          200:
            description: Task details
          404:
            description: Task not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["TES"]
        """
        try:
            task_id = int(id)
        except ValueError:
            return {"msg": f"Invalid task ID: {id}"}, HTTPStatus.BAD_REQUEST

        task = db.Task.get(task_id)
        if not task:
            return {"msg": f"Task id={id} not found"}, HTTPStatus.NOT_FOUND

        if not self.r.allowed_for_org(P.VIEW, task.init_org_id) and not (
            self.r.v_own.can() and g.user and task.init_user_id == g.user.id
        ):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        view = self._get_view()
        tes_task = vantage6_task_to_tes(task, view)

        return tes_task, HTTPStatus.OK


class TesCancelTask(TesBase):
    """Resource for /ga4gh/tes/v1/tasks/<id>:cancel"""

    @with_user
    def post(self, id: str):
        """Cancel a task
        ---
        description: >-
          Cancel a running task.

        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Task ID

        responses:
          200:
            description: Task cancelled
          404:
            description: Task not found
          400:
            description: Task already completed
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["TES"]
        """
        try:
            task_id = int(id)
        except ValueError:
            return {"msg": f"Invalid task ID: {id}"}, HTTPStatus.BAD_REQUEST

        task = db.Task.get(task_id)
        if not task:
            return {"msg": f"Task id={id} not found"}, HTTPStatus.NOT_FOUND

        if has_task_finished(task.status):
            return {
                "msg": f"Task {id} already finished with status '{task.status}'"
            }, HTTPStatus.BAD_REQUEST

        r_event = getattr(self.permissions, "event")
        if not r_event.s_glo.can():
            orgs = task.collaboration.organizations
            if not (r_event.s_col.can() and g.user.organization in orgs):
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        kill_task(task, self.socketio)

        return {}, HTTPStatus.OK
