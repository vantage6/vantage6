import logging

from flask import request, g
from flask_restful import Api
from http import HTTPStatus
from sqlalchemy import or_, and_
from names_generator import generate_name

from vantage6.common import logger_name
from vantage6.common.enums import LocalAction
from vantage6.server import db
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.server.permission import (
    Scope as S,
    Operation as P,
    PermissionManager,
    RuleCollection,
)
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.resource import only_for, with_user, ServicesResources
from vantage6.server.resource.common.input_schema import (
    SessionInputSchema,
    DataframeInitInputSchema,
    DataframeStepInputSchema,
    DataframeNodeUpdateSchema,
)
from vantage6.server.resource.common.output_schema import (
    SessionSchema,
    DataframeSchema,
)
from vantage6.server.resource.task import Tasks


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
        Sessions,
        path,
        endpoint="session_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Session,
        path + "/<int:id>",
        endpoint="session_with_id",
        methods=("GET", "PATCH", "DELETE"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        SessionDataframes,
        path + "/<int:session_id>/dataframe",
        endpoint="session_dataframe_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        SessionDataframe,
        path + "/<int:session_id>/dataframe/<string:dataframe_handle>",
        endpoint="session_dataframe_with_id",
        methods=("GET", "POST", "PATCH"),
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

    # view
    add(scope=S.GLOBAL, operation=P.VIEW, description="view any session")
    add(
        scope=S.COLLABORATION,
        operation=P.VIEW,
        description="view any session within your collaborations",
        assign_to_node=True,
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.VIEW,
        description="view any session initiated from your organization",
    )
    add(scope=S.OWN, operation=P.VIEW, description="view your own session")

    # create
    add(scope=S.OWN, operation=P.CREATE, description="create a new session")
    add(
        scope=S.ORGANIZATION,
        operation=P.CREATE,
        description="create a new session for all users within your organization",
    )
    add(
        scope=S.COLLABORATION,
        operation=P.CREATE,
        description="create a new session for all users within your collaboration",
    )

    # edit permissions.
    add(scope=S.OWN, operation=P.EDIT, description="edit your own session")
    add(
        scope=S.ORGANIZATION,
        operation=P.EDIT,
        description="edit any session initiated from your organization",
    )
    add(
        scope=S.COLLABORATION,
        operation=P.EDIT,
        description="edit any session within your collaboration",
        assign_to_node=True,
    )

    # delete permissions
    add(scope=S.OWN, operation=P.DELETE, description="delete your own session")
    add(
        scope=S.ORGANIZATION,
        operation=P.DELETE,
        description="delete any session initiated from your organization",
    )
    add(
        scope=S.COLLABORATION,
        operation=P.DELETE,
        description="delete any session within your collaborations",
    )
    add(scope=S.GLOBAL, operation=P.DELETE, description="delete any session")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
session_schema = SessionSchema()
dataframe_schema = DataframeSchema()

session_input_schema = SessionInputSchema()
dataframe_init_input_schema = DataframeInitInputSchema()
dataframe_step_input_schema = DataframeStepInputSchema()

dataframe_node_update_schema = DataframeNodeUpdateSchema()


class SessionBase(ServicesResources):
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)

    def can_view_session(self, session: db.Session) -> bool:
        """Check if the user can view the session"""
        if self.r.v_glo.can():
            return True

        if (
            self.r.v_col.can()
            and session.collaboration_id in self.obtain_auth_collaboration_ids()
        ):
            return True

        if (
            self.r.v_org.can()
            and session.organization_id == self.obtain_organization_id()
        ):
            return True

        if self.is_user() and self.r.v_own.can() and session.user_id == g.user.id:
            return True

        return False

    def create_session_task(
        self,
        session: db.Session,
        image: str,
        organizations: dict,
        database: dict,
        action: LocalAction,
        dataframe: db.Dataframe,
        description="",
        depends_on_ids=None,
    ) -> int:
        """Create a task to initialize a session"""

        if not depends_on_ids:
            depends_on_ids = []

        input_ = {
            "collaboration_id": session.collaboration_id,
            "study_id": session.study_id,
            "session_id": session.id,
            "name": f"Session initialization: {session.name}",
            "description": description,
            "image": image,
            "organizations": organizations,
            "databases": database,
            "depends_on_ids": depends_on_ids,
            "dataframe_id": dataframe.id,
        }
        # remove empty values
        input_ = {k: v for k, v in input_.items() if v is not None}
        return Tasks.post_task(
            input_, self.socketio, getattr(self.permissions, "task"), action
        )

    @staticmethod
    def delete_session(session: db.Session) -> None:
        """
        Deletes the session and all associated configurations.

        Parameters
        ----------
        session : db.Session
            Session to delete
        """
        log.debug(f"Deleting session id={session.id}")

        for dataframe in session.dataframes:
            dataframe.delete()

        for task in session.tasks:
            for result in task.results:
                result.delete()
            task.delete()

        session.delete()


class Sessions(SessionBase):

    @only_for(("user", "node"))
    def get(self):
        """Returns a list of sessions
        ---
        description: >-
          Get a list of sessions based on filters and user permissions\n\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Global|View|❌|❌|View all available sessions|\n
          |Session|Collaboration|View|✅|❌|View all available sessions within the
          scope of the collaboration|\n
          |Session|Organization|View|❌|❌|View all available sessions that have been
          initiated from a user within your organization|\n
          |Session|Own|View|❌|❌|View all sessions created by you

          Accessible to users.

        parameters:
        - in: query
          name: label
          schema:
            type: string
          description: >-
            Name to match with a LIKE operator. \n
            * The percent sign (%) represents zero, one, or multiple
            characters\n
            * underscore sign (_) represents one, single character
        - in: query
          name: user
          schema:
            type: integer
          description: User id
        - in: query
          name: user
          schema:
            type: integer
          description: User id
        - in: query
          name: collaboration
          schema:
            type: integer
          description: Collaboration id
        - in: query
          name: scope
          schema:
            type: string
          description: >-
            Scope of the session. Possible values are: GLOBAL, COLLABORATION,
            ORGANIZATION, OWN
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
          401:
            description: Unauthorized
          400:
            description: Improper values for pagination or sorting parameters

        security:
        - bearerAuth: []

        tags: ["Session"]
        """

        # Obtain the organization of the requester
        auth_org = self.obtain_auth_organization()
        args = request.args

        # query
        q = g.session.query(db.Session)
        g.session.commit()

        # filter by a field of this endpoint
        if "label" in args:
            q = q.filter(db.Session.label.like(args["label"]))
        if "user" in args:
            q = q.filter(db.Session.user_id == args["user"])
        if "collaboration" in args:
            q = q.filter(db.Session.collaboration_id == args["collaboration"])
        if "scope" in args:
            q = q.filter(db.Session.scope == args["scope"])

        # filter the list of organizations based on the scope. If you have collaboration
        # permissions you can see all sessions within the collaboration. If you have
        # organization permissions you can see all sessions withing your organization
        # and the sessions from other organization that have scope collaboration.
        # Finally when you have own permissions you can see the sessions that you have
        # created, the sessions from your organization with scope organization and you
        # can see the sessions in the collaboration that have a scope collaboration.
        if not self.r.v_glo.can():
            if self.r.v_col.can():
                q = q.filter(db.Session.collaboration_id.in_(auth_org.collaborations))
            elif self.r.v_org.can():
                q = q.filter(
                    or_(
                        db.Session.organization_id == auth_org.id,
                        and_(
                            db.Session.collaboration_id.in_(auth_org.collaborations),
                            db.Session.scope == S.COLLABORATION,
                        ),
                    )
                )
            elif self.r.v_own.can():
                q = q.filter(
                    or_(
                        db.Session.user_id == g.user.id,
                        and_(
                            db.Session.organization_id == auth_org.id,
                            db.Session.scope == S.ORGANIZATION,
                        ),
                        and_(
                            db.Session.collaboration_id.in_(auth_org.collaborations),
                            db.Session.scope == S.COLLABORATION,
                        ),
                    )
                )
            else:
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        # paginate the results
        try:
            page = Pagination.from_query(q, request, db.Session)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        # serialization of DB model
        return self.response(page, session_schema)

    @with_user
    def post(self):
        """Initiate new session
        ---
        description: >-
          Initialize a new session in a collaboration or study. A session always starts
          with a data-extraction step. In this extraction step, the data is extracted
          from the source database. Then a handle is returned to the user. This handle
          is a reference to the session data set. This handle can be used to add
          additional steps to the dataframe or to execute compute tasks on. A session
          can be scoped to the entire collaboration, the organization or only to the
          owner of the session. This way sessions can be shared with other users within
          the collaboration or organization.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Collaboration|Create|❌|❌|Create session to be used by the entire
          collaboration|\n
          |Session|Organization|Create|❌|❌|Create session to be used by your organization|\n
          |Session|Own|Create|❌|❌|Create session only to be used by you|\n

          Only accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Session'

        responses:
          201:
            description: Ok
          401:
            description: Unauthorized
          400:
            description: Session with that label already exists within the collaboration
                or Request body is incorrect
          404:
            description: Collaboration or study not found


        security:
        - bearerAuth: []

        tags: ["Session"]
        """
        # TODO if any of the steps fails... we need to rollback the entire session
        if not self.r.has_at_least_scope(S.OWN, P.CREATE):
            return {
                "msg": "You lack the permission to do that! 1"
            }, HTTPStatus.UNAUTHORIZED

        data = request.get_json()
        errors = session_input_schema.validate(data)

        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        # Check if the user has the permission to create a session for the scope
        scope = getattr(S, data["scope"].upper())
        if not self.r.has_at_least_scope(scope, P.CREATE):
            return {
                "msg": (
                    "You lack the permission to create a session for "
                    f"the {data['scope']} scope!"
                )
            }, HTTPStatus.UNAUTHORIZED

        collaboration: db.Collaboration = db.Collaboration.get(data["collaboration_id"])
        if not collaboration:
            return {"msg": "Collaboration not found"}, HTTPStatus.NOT_FOUND

        # When no label is provided, we generate a unique label.
        if "name" not in data:
            while db.Session.name_exists(
                propose_name := generate_name(), collaboration
            ):
                pass
            data["name"] = propose_name

        # In case the user provides a name, we check if the name already exists
        if db.Session.name_exists(data["name"], collaboration):
            return {
                "msg": "Session with that name already exists within the collaboration!"
            }, HTTPStatus.BAD_REQUEST

        # Create the Session object
        session = db.Session(
            name=data["name"],
            user_id=g.user.id,
            collaboration=collaboration,
            scope=scope,
            study_id=data.get("study_id"),
        )
        session.save()
        log.info(f"Session {session.id} created")

        return session_schema.dump(session, many=False), HTTPStatus.CREATED


class Session(SessionBase):

    @only_for(("user", "node"))
    def get(self, id):
        """View specific session
        ---
        description: >-
          Returns the session specified by the id\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Global|View|❌|❌|View any session|\n
          |Session|Collaboration|View|❌|❌|View any session within your
          collaborations|\n
          |Session|Organization|View|❌|❌|View any session that has been
          initiated from your organization or shared with your organization|\n
          |Session|Own|View|❌|❌|View any session you created or that is shared
          with you|\n

          Accessible to users.

        parameters:
        - in: path
          name: id
          schema:
            type: integer
          description: Session ID
          required: true

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

        # retrieve requested organization
        session: db.Session = db.Session.get(id)
        if not session:
            return {"msg": f"Session id={id} not found!"}, HTTPStatus.NOT_FOUND

        if not self.can_view_session(session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        return session_schema.dump(session, many=False), HTTPStatus.OK

    @only_for(("user",))
    def patch(self, id):
        """Update session
        ---
        description: >-
          Updates the scope or name of the session.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Collaboration|Edit|❌|❌|Update an session within
          the collaboration the user is part of|\n
          |Session|Organization|Edit|❌|❌|Update the session that is initiated from
          a user within your organization|\n
          |Session|Own|Edit|❌|❌|Update a session that you created|\n

          Accessible to users.

        parameters:
        - in: path
          name: id
          schema:
            type: integer
          description: Session ID
          required: true

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Name of the session
                  scope:
                    type: string
                    description: Scope of the session

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized
          404:
            description: Session not found
          400:
            decription: Session with that name already exists within the collaboration

        security:
        - bearerAuth: []

        tags: ["Session"]
        """
        # validate request body
        data = request.get_json()
        errors = session_input_schema.validate(data, partial=True)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        session: db.Session = db.Session.get(id)
        if not session:
            return {"msg": f"Session with id={id} not found"}, HTTPStatus.NOT_FOUND

        # If you are the owner of the session you only require edit permissions at
        # own level. In case you are not the owner, the session needs to be within
        # you scope in order to edit it.
        is_owner = session.owner.id == g.user.id
        if not (is_owner and self.r.has_at_least_scope(S.OWN, P.EDIT)):
            if not self.r.has_at_least_scope(session.scope, P.EDIT):
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        if "name" in data:
            if data["name"] != session.name and db.Session.name_exists(
                data["name"], session.collaboration
            ):
                return {
                    "msg": "Session with that name already exists within the "
                    "collaboration!"
                }, HTTPStatus.BAD_REQUEST

            session.name = data["name"]

        if "scope" in data:
            scope = getattr(S, data["scope"].upper())
            if not self.r.has_at_least_scope(scope, P.EDIT):
                return {
                    "msg": (
                        "You lack the permission to change the scope of the session "
                        f"to {data['scope']}!"
                    )
                }, HTTPStatus.UNAUTHORIZED

            session.scope = scope

        session.save()
        return session_schema.dump(session, many=False), HTTPStatus.OK

    @only_for(("user",))
    def delete(self, id):
        """Delete session
        ---
        description: >-
          Deletes the session specified by the id. This also deletes all node sessions
          and configurations that are part of the session.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Global|Delete|❌|❌|Delete any session|\n
          |Session|Collaboration|Delete|❌|❌|Delete any session within your
          collaborations|\n
          |Session|Organization|Delete|❌|❌|Delete any session that has been
          initiated from your organization|\n
          |Session|Own|Delete|❌|❌|Delete any session you created|\n

          Accessible to users.

        parameters:
        - in: path
          name: session_id
          schema:
            type: integer
          description: Session ID
          required: true

        responses:
          204:
            description: Ok
          401:
            description: Unauthorized
          404:
            description: Session not found

        security:
          - bearerAuth: []

        tags: ["Session"]
        """
        session: db.Session = db.Session.get(id)
        if not session:
            return {"msg": f"Session with id={id} not found"}, HTTPStatus.NOT_FOUND

        accepted = False

        if self.r.d_glo.can():
            accepted = True

        elif (
            self.r.d_col.can()
            and session.collaboration_id in self.obtain_auth_collaboration_ids()
        ):
            accepted = True

        elif (
            self.r.d_org.can()
            and session.organization_id == self.obtain_organization_id()
        ):
            accepted = True

        elif self.r.d_own.can() and session.user_id == g.user.id:
            accepted = True

        if not accepted:
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        self.delete_session(session)
        # TODO create socket event so the node knows that it should clear the session
        # data too. We also need to check on startup at the nodes if sessions need to be
        # deleted.

        return {"msg": f"Successfully deleted session id={id}"}, HTTPStatus.OK


class SessionDataframes(SessionBase):
    "/<int:session_id>/dataframe"

    @only_for(("user", "node"))
    def get(self, session_id):
        """view all dataframes of a session"""
        session: db.Session = db.Session.get(session_id)
        if not session:
            return {
                "msg": f"Session with id={session_id} not found"
            }, HTTPStatus.NOT_FOUND

        if not self.can_view_session(session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        q = g.session.query(db.Dataframe).filter_by(session_id=session_id)

        # check if pagination is disabled
        paginate = True
        if "no_pagination" in request.args and request.args["no_pagination"] == "1":
            paginate = False

        # paginate results
        try:
            page = Pagination.from_query(q, request, db.Dataframe, paginate=paginate)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.BAD_REQUEST

        return self.response(page, dataframe_schema)

    # TODO FM 16-7-2024: Permissions need to be added
    @only_for(("user",))
    def post(self, session_id):
        """Initiate a new dataframe for a session"""

        session: db.Session = db.Session.get(session_id)
        if not session:
            return {
                "msg": f"Session with id={session_id} not found"
            }, HTTPStatus.NOT_FOUND

        # A dataframe is a list of tasks that need to be executed in order to initialize
        # the session. A single session can have multiple dataframes, each with a
        # different database or different user inputs. Each dataframe can be identified
        # using a unique handle.
        data = request.get_json()
        errors = dataframe_init_input_schema.validate(data)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        collaboration = session.collaboration

        # This label is used to identify the database, this label should match the
        # label in the node configuration file. Each node can have multiple
        # databases.
        source_db_label = data["label"]

        # Multiple datasets can be created in a single session. This handle can be
        # used by the `preprocessing` and `compute` to identify the different
        # datasets that are send after the data extraction task. The handle can be
        # provided by the user, if not a unique handle is generated.
        if "handle" not in data:
            while (handle := generate_name()) and db.Dataframe.select(session, handle):
                pass
        else:
            handle = data["handle"]

        dataframe = db.Dataframe(
            session=session,
            handle=handle,
        )
        dataframe.save()

        # When a session is initialized, a mandatory data extraction step is
        # required. This step is the first step in the dataframe and is used to
        # extract the data from the source database.
        extraction_details = data["task"]
        response, status_code = self.create_session_task(
            session=session,
            image=extraction_details["image"],
            organizations=extraction_details["organizations"],
            # TODO FM 10-7-2024: we should make a custom type for this
            database=[{"label": source_db_label, "type": "source"}],
            description=(
                f"Data extraction step for session {session.name} ({session.id})."
                f"This session is in the {collaboration.name} collaboration. This "
                f"data extraction step uses the {source_db_label} database. And "
                f"will initialize the dataframe with the handle {handle}."
            ),
            action=LocalAction.DATA_EXTRACTION,
            dataframe=dataframe,
        )

        if status_code != HTTPStatus.CREATED:
            return response, status_code

        dataframe.last_session_task_id = response["id"]
        dataframe.save()

        return dataframe_schema.dump(dataframe), HTTPStatus.CREATED


class SessionDataframe(SessionBase):
    "/<int:session_id>/dataframe/<string:dataframe_handle>"

    @only_for(("user",))
    def get(self, session_id, dataframe_handle):
        """View specific dataframe"""

        session = db.Session.get(session_id)
        if not session:
            return {
                "msg": f"Session with id={session_id} not found"
            }, HTTPStatus.NOT_FOUND

        if not self.can_view_session(session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        dataframe = db.Dataframe.select(session, dataframe_handle)
        if not dataframe:
            return {
                "msg": f"Dataframe with handle={dataframe_handle} not found"
            }, HTTPStatus.NOT_FOUND

        return dataframe_schema.dump(dataframe, many=False), HTTPStatus.OK

    # TODO FM 16-7-2024: Permissions need to be added
    @only_for(("user",))
    def post(self, session_id, dataframe_handle):
        """Add a preprocessing step to a dataframe"""

        session: db.Session = db.Session.get(session_id)
        if not session:
            return {
                "msg": f"Session with id={session_id} not found"
            }, HTTPStatus.NOT_FOUND

        dataframe_step = request.get_json()
        errors = dataframe_step_input_schema.validate(dataframe_step)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        dataframe = db.Dataframe.select(session, dataframe_handle)
        if not dataframe:
            return {
                "msg": (
                    f"Dataframe with handle={dataframe_handle} in session={session.name} "
                    "not found!"
                )
            }, HTTPStatus.NOT_FOUND

        if not dataframe.last_session_task:
            return {
                "msg": (
                    f"Dataframe with handle={dataframe_handle} in session={session.name} "
                    "has no last task! Session is not properly initialized!"
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
        log.debug(f"Active tasks: {requires_tasks}")
        log.debug(f"Last task: {dataframe.last_session_task}")
        log.debug(f"compute tasks: {dataframe.active_compute_tasks}")

        # Meta data about the modifying task
        preprocessing_task = dataframe_step["task"]

        response, status_code = self.create_session_task(
            session=session,
            database=[{"label": dataframe_handle, "type": "handle"}],
            description=f"Preprocessing step for session {session.name}",
            depends_on_ids=[rt.id for rt in requires_tasks],
            action=LocalAction.PREPROCESSING,
            image=preprocessing_task["image"],
            organizations=preprocessing_task["organizations"],
            dataframe=dataframe,
        )
        # In case the task is not created we do not want to modify the chain of tasks.
        # The user can try again.
        if status_code != HTTPStatus.CREATED:
            return response, status_code

        dataframe.last_session_task_id = response["id"]
        dataframe.save()

        return dataframe_schema.dump(dataframe, many=False), HTTPStatus.CREATED

    @only_for(("node",))
    def patch(self, session_id, dataframe_handle):
        """Nodes report their column names"""

        data = request.get_json()
        errors = dataframe_node_update_schema.validate(data, many=True)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        session: db.Session = db.Session.get(session_id)

        if not session:
            return {
                "msg": f"Session with id={session_id} not found"
            }, HTTPStatus.NOT_FOUND

        dataframe = db.Dataframe.select(session, dataframe_handle)
        if not dataframe:
            return {
                "msg": f"Dataframe with handle={dataframe_handle} not found"
            }, HTTPStatus.NOT_FOUND

        # Validate that this node is part of the session
        if not session.collaboration_id == g.node.collaboration_id:
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # first we clear out all previous reported columns
        db_session = DatabaseSessionManager.get_session()
        db_session.query(db.Column).filter_by(dataframe_id=dataframe.id).delete()
        db_session.commit()

        for column in data:
            db.Column(
                dataframe=dataframe,
                name=column["name"],
                dtype=column["dtype"],
                node=g.node,
            ).save()

        return {"msg": "Columns updated"}, HTTPStatus.OK