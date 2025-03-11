import logging

from flask import request, g
from flask_restful import Api
from http import HTTPStatus
from sqlalchemy import or_, and_, select
from names_generator import generate_name
from marshmallow import ValidationError

from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmStepType, TaskDatabaseType
from vantage6.server import db
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.server.permission import (
    Scope as S,
    Operation as P,
    PermissionManager,
    RuleCollection,
)
from vantage6.server.resource import only_for, with_user, ServicesResources, with_node
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
        path + "/dataframe/<int:id>",
        endpoint="session_dataframe_with_id",
        methods=("GET", "PATCH", "DELETE"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        DataframePreprocessing,
        path + "/dataframe/<int:id>/preprocess",
        endpoint="session_dataframe_preprocessing",
        methods=("POST",),
        resource_class_kwargs=services,
    )
    api.add_resource(
        DataframeColumns,
        path + "/dataframe/<int:id>/column",
        endpoint="session_dataframe_column",
        methods=("POST",),
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
    )

    # delete permissions
    add(
        scope=S.OWN,
        operation=P.DELETE,
        description="delete your own session and dataframes",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.DELETE,
        description="delete any session or dataframe initiated from your organization",
    )
    add(
        scope=S.COLLABORATION,
        operation=P.DELETE,
        description="delete any session or dataframe within your collaborations",
    )
    add(
        scope=S.GLOBAL,
        operation=P.DELETE,
        description="delete any session or dataframe",
    )


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
        """
        Check if the user can view the session.

        Depending on the scope of the session, the user needs to have the correct
        permissions. The user can view the session if:

        - The user has global view permissions
        - The user has collaboration view permissions or the session is scoped to the
          collaboration AND the user is part of the collaboration of the session
        - The user has organization view permissions or the session is scoped to the
          organization AND the user is part of the organization of the session
        - The user has own view permissions AND the user is the owner of the session

        Note that viewing includes viewing both the sessions and the dataframes.

        Parameters
        ----------
        session : db.Session
            Session to check whether the user can view it

        Returns
        -------
        bool
            True if the user can view the session, False otherwise
        """
        if self.r.v_glo.can():
            return True

        if (
            self.r.v_col.can() or session.scope == S.COLLABORATION
        ) and session.collaboration_id in self.obtain_auth_collaboration_ids():
            return True

        if (
            self.r.v_org.can() or session.scope == S.ORGANIZATION
        ) and session.organization_id == self.obtain_organization_id():
            return True

        if self.is_user() and session.user_id == g.user.id:
            return True

        return False

    def can_edit_session(self, session: db.Session) -> bool:
        """
        Check if the user can edit the session.

        Depending on the scope of the session, the user needs to have the correct
        permissions. The user can edit the session if:

        - The user has collaboration edit permissions and the user is part of the
          collaboration of the session
        - The user has organization edit permissions and the user is part of the
          organization of the session
        - The user has own edit permissions AND the user is the owner of the session

        Note that editing includes:
        - Modifying the session properties
        - Adding / Modifying and deleting a dataframe

        Parameters
        ----------
        session : db.Session
            Session to check whether the user can edit it
        operation: P
            Operation to check for permissions

        Returns
        -------
        bool
            True if the user can edit the session, False otherwise
        """
        return self._can_session(session, P.EDIT)

    def can_delete_session(self, session: db.Session) -> bool:
        """
        Check if the user can delete the session.

        Depending on the scope of the session, the user needs to have the correct
        permissions. The user can delete the session if:

        - The user has collaboration delete permissions and the user is part of the
          collaboration of the session
        - The user has organization delete permissions and the user is part of the
          organization of the session
        - The user has own delete permissions AND the user is the owner of the session

        Note that deleting includes:
        - Deleting the session
        - Deleting all associated dataframes and tasks

        Parameters
        ----------
        session : db.Session
            Session to check whether the user can delete it

        Returns
        -------
        bool
            True if the user can delete the session, False otherwise
        """
        return self._can_session(session, P.DELETE)

    def _can_session(self, session: db.Session, operation: P) -> bool:
        """Helper for determining permissions for deleting and editing a session"""

        if operation not in (P.EDIT, P.DELETE):
            raise ValueError(f"Operation {operation} not supported!")

        op = "e" if operation == P.EDIT else "d"

        if (
            getattr(self.r, f"{op}_col").can()
            and session.collaboration_id in self.obtain_auth_collaboration_ids()
        ):
            return True

        if (
            getattr(self.r, f"{op}_org").can()
            and session.organization_id == self.obtain_organization_id()
        ):
            return True

        if (
            self.is_user()
            and getattr(self.r, f"{op}_own").can()
            and session.user_id == g.user.id
        ):
            return True

        return False

    def create_session_task(
        self,
        session: db.Session,
        image: str,
        organizations: dict,
        databases: list[dict],
        action: AlgorithmStepType,
        dataframe: db.Dataframe,
        description="",
        depends_on_ids=None,
        store_id=None,
        server_url=None,
    ) -> dict:
        """
        Create a task to initialize a session.

        Arguments
        ---------
        session : db.Session
            Session to create the task for
        image : str
            Docker image to use for the task
        organizations : dict
            Organizations that need to execute the task
        databases : list[dict]
            Databases used for the task
        action : AlgorithmStepType
            Action to perform (e.g. data extraction, preprocessing, etc)
        dataframe : db.Dataframe
            Dataframe to use for the task
        description : str
            Human readable description of the task
        depends_on_ids : list[int]
            List of task ids that this task depends on
        store_id : int
            Id of the store to use for the task
        server_url : str
            URL of the server to use for the task

        Returns
        -------
        dict
            Task object
        """

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
            "databases": databases,
            "depends_on_ids": depends_on_ids,
            "dataframe_id": dataframe.id,
            "store_id": store_id,
            "server_url": server_url,
        }
        # remove empty values
        input_ = {k: v for k, v in input_.items() if v is not None}
        return Tasks.post_task(
            input_,
            self.socketio,
            getattr(self.permissions, "task"),
            self.config,
            action,
        )


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
            name: name
            schema:
              type: string
            description: >-
              Name to match with a LIKE operator. \n
              * The percent sign (%) represents zero, one, or multiple
              characters\n
              * underscore sign (_) represents one, single character
          - in: query
            name: user_id
            schema:
              type: integer
            description: User id
          - in: query
            name: collaboration_id
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

        q = select(db.Session)

        # filter by a field of this endpoint
        if "name" in args:
            q = q.filter(db.Session.name.like(args["name"]))
        if "user_id" in args:
            q = q.filter(db.Session.user_id == args["user_id"])
        if "collaboration_id" in args:
            q = q.filter(db.Session.collaboration_id == args["collaboration_id"])
        if "scope" in args:
            q = q.filter(db.Session.scope == args["scope"].upper())

        # Filter the list of organizations based on the scope. If you have collaboration
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
                            db.Session.collaboration_id.in_(
                                self.obtain_auth_collaboration_ids()
                            ),
                            db.Session.scope == S.COLLABORATION,
                        ),
                    )
                )
            else:
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

        # Query and paginate the results
        try:
            page = Pagination.from_query(q, request, db.Session)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        return self.response(page, session_schema)

    @with_user
    def post(self):
        """Initiate new session
        ---
        description: >-
          Create a new session in a collaboration or study. A session can be scoped
          to the entire collaboration, the organization or only to the owner of the
          session. This way sessions can be shared with other users within the
          collaboration or organization. Note that users with organization,
          collaboration or global permissions can view all sessions within the
          that scope.

          A session is a container for dataframes and tasks. A session can have
          multiple dataframes, each extracted from the same or a different database.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Collaboration|Create|❌|❌|Create session to be used by the entire
          collaboration|\n
          |Session|Organization|Create|❌|❌|Create session to be used by your organization|\n
          |Session|Own|Create|❌|❌|Create session only to be used by you|\n

          It is important to note that a user who creates a session with scope own,
          does not mean the session is private. As this session is accessible to all
          users who have sufficient permissions within the collaboration or
          organization.

          Only accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Session'

        responses:
          201:
            description: Ok, created
          401:
            description: Unauthorized
          400:
            description: Session with that label already exists within the
                collaboration, Request body is incorrect, or study is not within the
                collaboration
          404:
            description: Collaboration or study not found


        security:
        - bearerAuth: []

        tags: ["Session"]
        """
        data = request.get_json(silent=True)
        try:
            data = session_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # Check if the user has the permission to create a session for the scope
        scope = getattr(S, data["scope"].upper())
        if not self.r.has_at_least_scope(scope, P.CREATE):
            return {
                "msg": (
                    "You lack the permission to create a session for "
                    f"the {data['scope'].upper()} scope!"
                )
            }, HTTPStatus.UNAUTHORIZED

        collaboration: db.Collaboration = db.Collaboration.get(data["collaboration_id"])
        if not collaboration:
            return {"msg": "Collaboration not found"}, HTTPStatus.NOT_FOUND

        # Check that the user is part of the collaboration
        if collaboration.id not in self.obtain_auth_collaboration_ids():
            return {
                "msg": (
                    "You lack the permission to create a session for this "
                    "collaboration!"
                )
            }, HTTPStatus.UNAUTHORIZED

        # When no label is provided, we generate a unique label.
        if data.get("name") is None:
            while db.Session.name_exists(
                proposed_name := generate_name(), collaboration
            ):
                pass
            data["name"] = proposed_name

        # In case the user provides a name, we check if the name already exists
        if db.Session.name_exists(data["name"], collaboration):
            return {
                "msg": "Session with that name already exists within the collaboration!"
            }, HTTPStatus.BAD_REQUEST

        # In case a study is provided we also need to check that this is within the
        # collaboration.
        if data.get("study_id"):
            study = db.Study.get(data["study_id"])
            if not study:
                return {"msg": "Study not found"}, HTTPStatus.NOT_FOUND

            if study.collaboration_id != collaboration.id:
                return {
                    "msg": "Study is not part of the collaboration!"
                }, HTTPStatus.BAD_REQUEST

            study_id = study.id
        else:
            study_id = None

        # Create the Session object
        session = db.Session(
            name=data["name"],
            user_id=g.user.id,
            collaboration=collaboration,
            scope=scope,
            study_id=study_id,
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
          |Session|Collaboration|View|✅|❌|View any session within your
          collaborations|\n
          |Session|Organization|View|❌|❌|View any session that has been
          initiated from your organization or shared with your organization|\n
          |Session|Own|View|❌|❌|View any session you created or that is shared
          with you|\n

          Accessible to users and nodes.

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
        session: db.Session = db.Session.get(id)
        if not session:
            return {"msg": f"Session id={id} not found!"}, HTTPStatus.NOT_FOUND

        if not self.can_view_session(session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        return session_schema.dump(session, many=False), HTTPStatus.OK

    @with_user
    def patch(self, id):
        """Update session
        ---
        description: >-
          Update the scope or name of the session.\n

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
                    description: Scope of the session, possible values are GLOBAL,
                        COLLABORATION, ORGANIZATION, OWN

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
        data = request.get_json(silent=True)
        try:
            data = session_input_schema.load(data, partial=True)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        session: db.Session = db.Session.get(id)
        if not session:
            return {"msg": f"Session with id={id} not found"}, HTTPStatus.NOT_FOUND

        if not self.can_edit_session(session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        if data.get("name"):
            if data["name"] != session.name and db.Session.name_exists(
                data["name"], session.collaboration
            ):
                return {
                    "msg": (
                        "Session with that name already exists within the "
                        "collaboration!"
                    )
                }, HTTPStatus.BAD_REQUEST

            session.name = data["name"]

        if data.get("scope"):
            scope = getattr(S, data["scope"].upper(), None)
            if not scope:
                return {
                    "msg": f"Scope must be one of the following: {S.list()}"
                }, HTTPStatus.BAD_REQUEST
            if not self.r.has_at_least_scope(scope, P.EDIT):
                return {
                    "msg": (
                        "You lack the permission to change the scope of the session "
                        f"to {data['scope'].upper()}!"
                    )
                }, HTTPStatus.UNAUTHORIZED

            session.scope = scope

        session.save()
        return session_schema.dump(session, many=False), HTTPStatus.OK

    @with_user
    def delete(self, id):
        """Delete session
        ---
        description: >-
          Deletes the session specified by the ID. When the `delete_dependents` option
          is set to `true` also all associated dataframes and tasks are deleted. \n

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
          - in: query
            name: delete_dependents
            schema:
                type: boolean
            description: >-
                Delete all dependents of the session. This includes dataframes and
                tasks that are part of the

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

        if not self.can_delete_session(session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        delete_dependents = request.args.get("delete_dependents", False)
        if (session.dataframes or session.tasks) and not delete_dependents:
            return {
                "msg": (
                    "This session contains tasks and dataframes. Please delete them "
                    "first or set `delete_dependents` to `true` to delete them together"
                    " with the session."
                )
            }, HTTPStatus.BAD_REQUEST

        # This only deletes the session metadata from the server
        session.delete()

        return {"msg": f"Successfully deleted session id={id}"}, HTTPStatus.OK


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

        # This label is used to identify the database, this label should match the
        # label in the node configuration file. Each node can have multiple
        # databases.
        source_db_label = data["label"]

        # Create the dataframe
        # TODO guarantee that the name is unique (there is an issue for this)
        df_name = data.get("name", generate_name())
        dataframe = db.Dataframe(
            session=session,
            name=df_name,
            db_label=source_db_label,
        )
        dataframe.save()

        # When a session is initialized, a mandatory data extraction step is
        # required. This step is the first step in the dataframe and is used to
        # extract the data from the source database.
        extraction_details = data["task"]
        if "description" in extraction_details and extraction_details["description"]:
            description = extraction_details["description"]
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
                image=extraction_details["image"],
                organizations=extraction_details["organizations"],
                # TODO FM 10-7-2024: we should make a custom type for this
                databases=[{"label": source_db_label, "type": "source"}],
                description=description,
                action=AlgorithmStepType.DATA_EXTRACTION,
                dataframe=dataframe,
                store_id=extraction_details.get("store_id"),
                server_url=extraction_details.get("server_url"),
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

        if not self.can_delete_session(dataframe.session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        df_name = dataframe.name
        session_id = dataframe.session_id

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
            "msg": f"Successfully deleted dataframe {df_name} from session {session_id}"
        }, HTTPStatus.OK


class DataframePreprocessing(SessionBase):

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
            dataframe_step = dataframe_step_input_schema.load(dataframe_step)
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
                {"label": dataframe.db_label, "type": TaskDatabaseType.DATAFRAME}
            ],
            description=description,
            depends_on_ids=[rt.id for rt in requires_tasks],
            action=AlgorithmStepType.PREPROCESSING,
            image=preprocessing_task["image"],
            organizations=preprocessing_task["organizations"],
            dataframe=dataframe,
            store_id=preprocessing_task.get("store_id"),
            server_url=preprocessing_task.get("server_url"),
        )
        # In case the task is not created we do not want to modify the chain of tasks.
        # The user can try again.
        if status_code != HTTPStatus.CREATED:
            return response, status_code

        dataframe.last_session_task_id = response["id"]
        dataframe.save()

        return dataframe_schema.dump(dataframe, many=False), HTTPStatus.CREATED


class DataframeColumns(SessionBase):

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

        return {"msg": "Columns updated"}, HTTPStatus.OK
