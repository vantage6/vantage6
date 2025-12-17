import logging
from http import HTTPStatus

from flask import g, request
from flask_restful import Api
from marshmallow import ValidationError
from names_generator import generate_name
from sqlalchemy import select

from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmStepType, TaskDatabaseType

from vantage6.backend.common.resource.error_handling import handle_exceptions
from vantage6.backend.common.resource.pagination import Pagination

from vantage6.server import db
from vantage6.server.dataclass import CreateTaskDB
from vantage6.server.model import DataframeToBeDeletedAtNode
from vantage6.server.resource import only_for, with_node, with_user
from vantage6.server.resource.common.input_schema import (
    DataframeInitInputSchema,
    DataframeNodeUpdateSchema,
    DataframePreprocessingInputSchema,
)
from vantage6.server.resource.common.output_schema import (
    DataframeSchema,
)
from vantage6.server.resource.session import SessionBase
from vantage6.server.websockets import send_delete_dataframe_event

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the session resource.

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
        SessionDataframes,
        api_base + "/session/<int:session_id>/dataframe",
        endpoint="session_dataframe_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        SessionDataframe,
        api_base + "/session/dataframe/<int:id>",
        endpoint="session_dataframe_with_id",
        methods=("GET", "DELETE"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        DataframePreprocessing,
        api_base + "/session/dataframe/<int:id>/preprocess",
        endpoint="session_dataframe_preprocessing",
        methods=("POST",),
        resource_class_kwargs=services,
    )
    api.add_resource(
        DataframeColumns,
        api_base + "/session/dataframe/<int:id>/column",
        endpoint="session_dataframe_column",
        methods=("POST",),
        resource_class_kwargs=services,
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
dataframe_schema = DataframeSchema()

dataframe_init_input_schema = DataframeInitInputSchema()
dataframe_preprocessing_input_schema = DataframePreprocessingInputSchema()

dataframe_node_update_schema = DataframeNodeUpdateSchema()


class SessionDataframes(SessionBase):
    @only_for(("user", "node"))
    def get(self, session_id):
        """view all dataframes in a session
        ---
        description: >-
          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Global|View|❌|❌|View any session|\n
          |Session|Collaboration|View|✅|❌|View all dataframes within the session|\n
          |Session|Organization|View|❌|❌|View any dataframe that has been
          initiated from your organization or shared with your organization within the
          session|\n
          |Session|Own|View|❌|❌|View any dataframe you created or that is shared
          with you within the session|\n

          Accessible to users and nodes.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Session ID
            required: true
          - in: query
            name: no_pagination
            schema:
              type: integer
            description: >-
              Disable pagination. When set to 1, pagination is disabled and all
              results are returned at once.
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

        responses:
          200:
            description: Ok
          404:
            description: Session not found
          401:
            description: Unauthorized

        security:
        - bearerAuth: []

        tags: ["Session"]
        """
        session: db.Session = db.Session.get(session_id)
        if not session:
            return {
                "msg": f"Session with id={session_id} not found"
            }, HTTPStatus.NOT_FOUND

        if not self.can_view_session(session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        q = select(db.Dataframe).filter_by(session_id=session_id)

        # check if pagination is disabled
        paginate = not (
            "no_pagination" in request.args and request.args["no_pagination"] == "1"
        )

        # paginate results
        try:
            page = Pagination.from_query(q, request, db.Dataframe, paginate=paginate)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.BAD_REQUEST

        return self.response(page, dataframe_schema)

    @handle_exceptions
    @with_user
    def post(self, session_id):
        """Create a new dataframe in a session
        ---
        description: >-
          Create a new dataframe in a session. The first step in creating the data
          frame is to extract the data from the source database. This is done by
          creating a task that extracts the data from the source database. The task
          should therefore also be defined in the request body.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Collaboration|Edit|❌|❌|Create dataframe in any session in your
          collaboration|\n
          |Session|Organization|Edit|❌|❌|Create dataframe in any session from your
          organization|\n
          |Session|Own|Edit|❌|❌|Create dataframe in a session owned by you|\n

          Only accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DataFrame'

        responses:
          201:
            description: Ok, created
          401:
            description: Unauthorized
          400:
            description: The request body is incorrect, or an illegal combination of
                parameters is provided
          404:
            description: Session not found


        security:
        - bearerAuth: []

        tags: ["Session"]
        """
        session: db.Session = db.Session.get(session_id)
        if not session:
            return {
                "msg": f"Session with id={session_id} not found"
            }, HTTPStatus.NOT_FOUND

        if not self.can_edit_session(session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # A dataframe is a list of tasks that need to be executed in order to initialize
        # the session. A single session can have multiple dataframes, each with a
        # different database or different user inputs.
        data = request.get_json(silent=True)
        try:
            data = dataframe_init_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        collaboration = session.collaboration

        task = data["task"]
        image_with_hash, _, _ = self.get_algorithm(
            task.get("store_id"),
            session.collaboration_id,
            task["image"],
        )

        self.__set_session_image(collaboration, image_with_hash, session)

        # This label is used to identify the database, this label should match the
        # label in the node configuration file. Each node can have multiple
        # databases.
        source_db_label = data["label"]

        # Create the dataframe
        if df_name := data.get("name"):
            if db.Dataframe.name_exists(df_name):
                return {
                    "msg": f"Dataframe with name {df_name} already exists. Duplicate "
                    "names are not allowed because they are stored on nodes by that "
                    "name."
                }, HTTPStatus.BAD_REQUEST

        else:
            while True:
                df_name = generate_name()
                if not db.Dataframe.name_exists(df_name):
                    break
        dataframe = db.Dataframe(
            session=session,
            name=df_name,
            db_label=source_db_label,
        )
        dataframe.save()

        # When a session is initialized, a mandatory data extraction step is
        # required. This step is the first step in the dataframe and is used to
        # extract the data from the source database.

        if task.get("description"):
            description = task["description"]
        else:
            description = (
                f"Data extraction step for session {session.name} ({session.id})."
                f"This session is in the {collaboration.name} collaboration. Data "
                f"extraction is done on the {source_db_label} database, and the "
                f"dataframe name will be {df_name}."
            )

        try:
            response, status_code = self.create_session_task(
                session=session,
                image=task["image"],
                method=task["method"],
                organizations=task["organizations"],
                databases=[
                    [
                        CreateTaskDB(
                            label=source_db_label, type=TaskDatabaseType.SOURCE
                        ).to_dict()
                    ]
                ],
                description=description,
                action=AlgorithmStepType.DATA_EXTRACTION,
                dataframe=dataframe,
                store_id=task.get("store_id"),
            )
        except Exception as e:
            dataframe.delete()
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        if status_code != HTTPStatus.CREATED:
            dataframe.delete()
            return response, status_code

        dataframe.last_session_task_id = response["id"]
        dataframe.save()

        return dataframe_schema.dump(dataframe), HTTPStatus.CREATED

    def __set_session_image(
        self, collaboration: db.Collaboration, image: str, session: db.Session
    ) -> None:
        """
        Set the session image if session is restricted to same image and it is not
        set.
        """
        if collaboration.session_restrict_to_same_image and not session.image:
            # this is the first task in the session, so we can set the image
            session.image = image
            session.save()


class SessionDataframe(SessionBase):
    @with_user
    def get(self, id):
        """View specific dataframe
        ---
        description: >-
          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Global|View|❌|❌|View any session|\n
          |Session|Collaboration|View|✅|❌|View any dataframe within the session|\n
          |Session|Organization|View|❌|❌|View any dataframe that has been
          initiated from your organization or shared with your organization within the
          session|\n
          |Session|Own|View|❌|❌|View any session you created or that is shared
          with you within the session|\n

          Only accessible by users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Dataframe ID
            required: true

        responses:
          200:
            description: Ok
          404:
            description: Session or DataFrame not found
          401:
            description: Unauthorized

        security:
        - bearerAuth: []

        tags: ["Session"]
        """

        dataframe: db.Dataframe = db.Dataframe.get(id)
        if not dataframe:
            return {"msg": f"Dataframe with id={id} not found"}, HTTPStatus.NOT_FOUND

        if not self.can_view_session(dataframe.session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        return dataframe_schema.dump(dataframe, many=False), HTTPStatus.OK

    @with_user
    def delete(self, id):
        """Delete dataframe
        ---
        description: >-
          Delete the dataframe. When the `delete_dependents` option is set to `true`,
          also all associated columns are deleted. \n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Global|Delete|❌|❌|Delete any dataframe|\n
          |Session|Collaboration|Delete|❌|❌|Delete any dataframe within the
          collaboration the user is part of|\n
          |Session|Organization|Delete|❌|❌|Delete any dataframe that is initiated
          from your organization|\n
          |Session|Own|Delete|❌|❌|Delete any dataframe you created|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Dataframe ID
            required: true

        responses:
            204:
                description: Ok
            401:
                description: Unauthorized
            404:
                description: Session or DataFrame not found

        security:
            - bearerAuth: []

        tags: ["Session"]
        """
        dataframe: db.Dataframe = db.Dataframe.get(id)
        if not dataframe:
            return {"msg": f"Dataframe with id={id} not found"}, HTTPStatus.NOT_FOUND

        if not self.can_edit_session(dataframe.session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        self._delete_dataframe_at_nodes(dataframe)

        # Delete alls that are part of this dataframe
        for column in dataframe.columns:
            column.delete()

        # Delete the dataframe itself from the server
        dataframe.delete()

        # TODO instruct nodes to delete the dataframe, consider the traceability of the
        # dataframe. Simply deleting the dataframe is not good, we should track it in
        # the session log or something.
        # https://github.com/vantage6/vantage6/issues/1567

        return {
            "msg": f"Successfully deleted dataframe {dataframe.name} from session "
            f"{dataframe.session_id}"
        }, HTTPStatus.OK

    def _delete_dataframe_at_nodes(self, dataframe: db.Dataframe) -> None:
        """
        Delete the dataframe at all nodes.
        """
        # store that node dataframes are to be deleted
        for node in dataframe.session.collaboration.nodes:
            df_to_be_deleted = DataframeToBeDeletedAtNode(
                dataframe_name=dataframe.name,
                session_id=dataframe.session_id,
                node_id=node.id,
            )
            df_to_be_deleted.save()

        # send socket event to nodes to delete the dataframe. Nodes that are online
        # will delete the dataframe from their local storage and respond with a socket
        # event to the server. The server will then delete the record created above
        # from the database. Other records will be deleted when the node comes online
        # again.
        send_delete_dataframe_event(
            self.socketio,
            dataframe.name,
            dataframe.session_id,
            dataframe.session.collaboration_id,
        )


class DataframePreprocessing(SessionBase):
    @handle_exceptions
    @with_user
    def post(self, id):
        """Add a preprocessing step to a dataframe
        ---
        description: >-
          Add a preprocessing step to a dataframe. A preprocessing step is a task that
          modifies the data in the dataframe. This can be used to clean the data, to
          normalize the data, to remove outliers, etc.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Collaboration|Edit|❌|❌|Modify dataframe in any session in your
          collaboration|\n
          |Session|Organization|Edit|❌|❌|Modify dataframe in any session from your
          organization|\n
          |Session|Own|Edit|❌|❌|Modify dataframe in a session owned by you|\n

          Only accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Dataframe ID
            required: true

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  task:
                    type: object
                    properties:
                      image:
                        type: string
                        description: Name of the image to use for the preprocessing task
                      organizations:
                        type: object
                        description: Organization and their input for this preprocessing
                          task

        responses:
          201:
            description: Ok, created
          401:
            description: Unauthorized
          400:
            description: The request body is incorrect, or an illigal combination of
                parameters is provided
          404:
            description: Session not found


        security:
        - bearerAuth: []

        tags: ["Session"]
        """
        dataframe: db.Dataframe = db.Dataframe.get(id)
        if not dataframe:
            return {"msg": f"Dataframe with id={id} not found"}, HTTPStatus.NOT_FOUND

        if not self.can_edit_session(dataframe.session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        dataframe_step = request.get_json(silent=True)
        try:
            dataframe_step = dataframe_preprocessing_input_schema.load(dataframe_step)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        session = dataframe.session
        if not dataframe.last_session_task:
            return {
                "msg": (
                    f"Dataframe {dataframe.name} (id={dataframe.id}) in "
                    f"session={session.name} has no last task! Session is not properly "
                    "initialized!"
                )
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        # Before modifying the session dataframe:
        #
        # 1. all computation tasks need to be finished. This is to prevent that the data
        #    is modified while it is being processed. Note that these run in parallel,
        #    so we need to check if all tasks are finished.
        # 2. all previous preprocessing steps need to be finished. These run in
        #    sequence, so we only need to check the latest modifying task.
        requires_tasks = dataframe.active_compute_tasks
        requires_tasks.append(dataframe.last_session_task)

        # Meta data about the modifying task
        preprocessing_task = dataframe_step["task"]
        if "description" in preprocessing_task and preprocessing_task["description"]:
            description = preprocessing_task["description"]
        else:
            description = (
                f"Preprocessing step for session {session.name} ({session.id})."
                f"This session is in the {session.collaboration.name} collaboration. "
                f"This preprocessing step will modify dataframe {dataframe.id} "
            )

        response, status_code = self.create_session_task(
            session=session,
            databases=[
                [
                    {
                        "dataframe_id": dataframe.id,
                        "type": TaskDatabaseType.DATAFRAME.value,
                    }
                ]
            ],
            description=description,
            depends_on_ids=[rt.id for rt in requires_tasks],
            action=AlgorithmStepType.PREPROCESSING,
            image=preprocessing_task["image"],
            method=preprocessing_task["method"],
            organizations=preprocessing_task["organizations"],
            dataframe=dataframe,
            store_id=preprocessing_task.get("store_id"),
        )
        # In case the task is not created we do not want to modify the chain of tasks.
        # The user can try again.
        if status_code != HTTPStatus.CREATED:
            return response, status_code

        dataframe.last_session_task_id = response["id"]
        dataframe.save()

        return dataframe_schema.dump(dataframe, many=False), HTTPStatus.CREATED


class DataframeColumns(SessionBase):
    @handle_exceptions
    @with_node
    def post(self, id):
        """Nodes report their column names
        ---
        description: >-
          Endpoints used by nodes to report dataframe metadata.\n

          Only accessible by nodes.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Dataframe ID
            required: true

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Name of the column
                  dtype:
                    type: string
                    description: Data type of the column

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized, node trying to report columns is not part of the
                collaboration
          404:
            description: Session or DataFrame not found
          400:
            description: Incorrect request body, see message for details

        security:
        - bearerAuth: []

        tags: ["Session"]
        """
        data = request.get_json(silent=True)
        try:
            data = dataframe_node_update_schema.load(data, many=True)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        dataframe: db.Dataframe = db.Dataframe.get(id)
        if not dataframe:
            return {"msg": f"Dataframe with id={id} not found"}, HTTPStatus.NOT_FOUND

        # Validate that this node is part of the session
        if not dataframe.session.collaboration_id == g.node.collaboration_id:
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # first we clear out all previous reported columns for this node
        db.Column.clear(dataframe.id, g.node.id)

        for column in data:
            db.Column(
                dataframe=dataframe,
                name=column["name"],
                dtype=column["dtype"],
                node=g.node,
            ).save()

        return {"msg": "Columns updated"}, HTTPStatus.CREATED
