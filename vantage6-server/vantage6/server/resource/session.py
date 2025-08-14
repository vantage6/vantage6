import logging
from http import HTTPStatus

from flask import g, request
from flask_restful import Api
from marshmallow import ValidationError
from names_generator import generate_name
from sqlalchemy import and_, or_, select

from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmStepType

from vantage6.backend.common.resource.pagination import Pagination

from vantage6.server import db
from vantage6.server.dataclass import CreateTaskDB
from vantage6.server.permission import (
    Operation as P,
    PermissionManager,
    RuleCollection,
    Scope as S,
)
from vantage6.server.resource import only_for, with_user
from vantage6.server.resource.common.input_schema import SessionInputSchema
from vantage6.server.resource.common.output_schema import SessionSchema
from vantage6.server.resource.common.task_post_base import TaskPostBase

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

session_input_schema = SessionInputSchema()


class SessionBase(TaskPostBase):
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
        ) and session.owner.organization_id == self.obtain_organization_id():
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

        if operation == P.DELETE:
            if getattr(self.r, f"{op}_glo").can():
                return True

        if (
            getattr(self.r, f"{op}_col").can()
            and session.collaboration_id in self.obtain_auth_collaboration_ids()
            and session.scope <= S.COLLABORATION
        ):
            return True

        if (
            getattr(self.r, f"{op}_org").can()
            and session.owner.organization_id == self.obtain_organization_id()
            and S(session.scope) <= S.ORGANIZATION
        ):
            return True

        if (
            self.is_user()
            and getattr(self.r, f"{op}_own").can()
            and session.user_id == g.user.id
            and session.scope == S.OWN
        ):
            return True

        return False

    def create_session_task(
        self,
        session: db.Session,
        image: str,
        method: str,
        organizations: dict,
        databases: list[CreateTaskDB],
        action: AlgorithmStepType,
        dataframe: db.Dataframe,
        description="",
        depends_on_ids=None,
        store_id=None,
    ) -> dict:
        """
        Create a task to initialize a session.

        Arguments
        ---------
        session : db.Session
            Session to create the task for
        image : str
            Docker image to use for the task
        method : str
            Method to use for the task
        organizations : dict
            Organizations that need to execute the task
        databases : list[list[dict]]
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
            "name": f"Session initialization ({session.name})",
            "description": description,
            "image": image,
            "method": method,
            "organizations": organizations,
            "databases": databases,
            "depends_on_ids": depends_on_ids,
            "dataframe_id": dataframe.id,
            "store_id": store_id,
        }
        # remove empty values
        input_ = {k: v for k, v in input_.items() if v is not None}
        return self.post_task(
            input_,
            getattr(self.permissions, "task"),
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
                q = q.filter(
                    db.Session.collaboration_id.in_(
                        self.obtain_auth_collaboration_ids()
                    )
                )
            elif self.r.v_org.can():
                q = q.join(db.User, db.Session.user_id == db.User.id).filter(
                    or_(
                        and_(
                            db.User.organization_id == auth_org.id,
                            db.Session.user_id == db.User.id,
                        ),
                        and_(
                            db.Session.collaboration_id.in_(
                                self.obtain_auth_collaboration_ids()
                            ),
                            db.Session.scope == S.COLLABORATION,
                        ),
                    )
                )
            else:
                q = q.join(db.User, db.Session.user_id == db.User.id).filter(
                    or_(
                        db.Session.user_id == g.user.id,
                        and_(
                            db.User.organization_id == auth_org.id,
                            db.Session.user_id == db.User.id,
                            db.Session.scope == S.ORGANIZATION,
                        ),
                        and_(
                            db.Session.collaboration_id.in_(
                                self.obtain_auth_collaboration_ids()
                            ),
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
                    description: Scope of the session, possible values are
                      'collaboration', 'organization' and 'own'

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

        for dataframe in session.dataframes:
            dataframe.delete()
        for task in session.tasks:
            task.delete()

        # This only deletes the session metadata from the server
        session.delete()

        return {"msg": f"Successfully deleted session id={id}"}, HTTPStatus.OK
