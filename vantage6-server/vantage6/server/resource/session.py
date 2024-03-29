import logging

from flask import request, g
from flask_restful import Api
from http import HTTPStatus
from sqlalchemy import or_, and_

from vantage6.common import logger_name
from vantage6.server import db
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.server.permission import (
    Scope as S,
    Operation as P,
    PermissionManager,
    RuleCollection,
)
from vantage6.server.resource import only_for, with_user, ServicesResources
from vantage6.server.resource.common.input_schema import (
    SessionInputSchema,
    NodeSessionInputSchema,
)
from vantage6.server.resource.common.output_schema import (
    SessionSchema,
    NodeSessionSchema,
)


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
        NodeSessions,
        path + "/<int:session_id>/node",
        endpoint="node_session_without_id",
        methods=(
            "GET",
            "PATCH",
        ),
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
session_input_schema = SessionInputSchema()
node_session_schema = NodeSessionSchema()
node_session_input_schema = NodeSessionInputSchema()


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


class Sessions(SessionBase):

    @only_for(("user", "node"))
    def get(self):
        """Returns a list of sessions
        ---
        description: >-
            Get a list of sessions based on filters and user permissions\n

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
        """Create new session
        ---
        description: >-
          Creates a new session in a collaboration\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Session|Collaboration|Create|❌|❌|Create session to be used by the entire
          collaboration|\n
          |Session|Organization|Create|❌|❌|Create session to be used by your organization|\n
          |Session|Own|Create|❌|❌|Create session only to be used by you|\n

          Accessible to users.

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
          404:
            description: Collaboration not found

        security:
          - bearerAuth: []

        tags: ["Session"]
        """
        if not self.r.has_at_least_scope(S.OWN, P.CREATE):
            return {
                "msg": "You lack the permission to do that!"
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

        # Check if the session label already exists in the collaboration
        if db.Session.label_exists(data["label"], collaboration):
            return {
                "msg": "Session with that label already exists within the collaboration!"
            }, HTTPStatus.BAD_REQUEST

        # Create parent session object.
        session = db.Session(
            label=data["label"],
            user_id=g.user.id,
            collaboration=collaboration,
            scope=scope,
        )
        session.save()
        # Each node gets assigned a NodeSession to keep track of each individual node's
        # state.
        for node in collaboration.nodes:
            db.NodeSession(
                session=session,
                node=node,
            ).save()

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
            description: Session id
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

    @with_user
    def patch(self, id):
        """Update session
        ---
        description: >-
          Updates the scope or label of the session.\n

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
            description: Session id
            required: true

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  label:
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
            decription: Session with that label already exists within the collaboration

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
        is_owner = session.owner_id == g.user.id
        if not (is_owner and self.r.has_at_least_scope(S.OWN, P.EDIT)):
            if not self.r.has_at_least_scope(session.scope, P.EDIT):
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        if "label" in data:
            if db.Session.label_exists(data["label"], session.collaboration_id):
                return {
                    "msg": "Session with that label already exists within the "
                    "collaboration!"
                }, HTTPStatus.BAD_REQUEST

            session.label = data["label"]

        if "scope" in data:
            if not self.r.has_at_least_scope(data["scope"], P.EDIT):
                return {
                    "msg": (
                        "You lack the permission to change the scope of the session "
                        f"to {data['scope']}!"
                    )
                }, HTTPStatus.UNAUTHORIZED

            session.scope = data["scope"]

        session.save()
        return session_schema.dump(session, many=False), HTTPStatus.OK

    @only_for(("user",))
    def delete(self, id):
        """Delete session
        ---
        description: >-
          Deletes the session specified by the id\n

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
            name: id
            schema:
              type: integer
            description: Session id
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

        for node_session in session.node_sessions:
            for config in node_session.configurations:
                config.delete()
            node_session.delete()

        session.delete()
        return {"msg": f"Successfully deleted session id={id}"}, HTTPStatus.OK


class NodeSessions(SessionBase):

    @only_for(("user", "node"))
    def get(self, session_id):
        """Get node session
        ---
        description: >-
        Returns the 'node sessions' for the specified session\n

        ### Permissions\n
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

        Accessible to users.

        parameters:
        - in: path
            name: session_id
            schema:
            type: integer
            description: Session id
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
        session: db.Session = db.Session.get(session_id)
        if not session:
            return {
                "msg": f"Session with id={session_id} not found"
            }, HTTPStatus.NOT_FOUND

        if not self.can_view_session(session):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        return node_session_schema.dump(session.node_sessions, many=True), HTTPStatus.OK

    @only_for(("node",))
    def patch(self, session_id):
        """Update node session
        ---
        description: >-
        Update the state of the node session\n

        ### Permissions\n
        Only accessable by nodes.

        Note that this endpoint deletes all config options when new configuration
        settings are provided.

        parameters:
        - in: path
            name: session_id
            schema:
            type: integer
            description: Session id
            required: true

        requestBody:
        content:
            application/json:
            schema:
                properties:
                state:
                    type: string
                    description: State of the node session

        responses:
        200:
            description: Ok
        401:
            description: Unauthorized
        404:
            description: Session not found

        security:
        - bearerAuth: []

        tags: ["Session"]
        """
        data = request.get_json()
        errors = node_session_input_schema.validate(data)
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

        node_session: db.NodeSession = db.NodeSession.get_by_node_and_session(
            g.node.id, session.id
        )
        if not node_session:
            return {
                "msg": f"Node session with node id={g.node.id} and session "
                f"id={session.id} not found"
            }, HTTPStatus.NOT_FOUND

        if "config" in data:
            # Delete old configuration
            for item in node_session.config:
                item.delete()
            # add new
            for config in data["config"]:
                db.NodeSessionConfig(
                    node_session=node_session, key=config["key"], value=config["value"]
                ).save()

        if "state" in data:
            node_session.state = data["state"]
            node_session.save()

        return node_session_schema.dump(node_session, many=False), HTTPStatus.OK
