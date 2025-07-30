import logging
from http import HTTPStatus

from flask import g
from flask.globals import request
from flask_restful import Api
from sqlalchemy import or_, select

from vantage6.common import logger_name

from vantage6.backend.common.resource.error_handling import (
    BadRequestError,
    NotFoundError,
    UnauthorizedError,
    handle_exceptions,
)
from vantage6.backend.common.resource.input_schema import ServerRoleInputSchema
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.backend.common.resource.role import (
    apply_user_filter,
    can_delete_dependents,
    check_default_role,
    filter_by_attribute,
    get_role,
    get_rule,
    get_rules,
    update_role,
    validate_request_body,
    validate_user_exists,
)

from vantage6.server import db
from vantage6.server.default_roles import DefaultRole
from vantage6.server.model.rule import Operation, Scope
from vantage6.server.permission import (
    Operation as P,
    PermissionManager,
    RuleCollection,
)
from vantage6.server.resource import (
    ServicesResources,
    get_org_ids_from_collabs,
    with_user,
)
from vantage6.server.resource.common.output_schema import RoleSchema, RuleSchema

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the role resource.

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
        Roles,
        path,
        endpoint="role_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Role,
        path + "/<int:id>",
        endpoint="role_with_id",
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
    add(scope=Scope.GLOBAL, operation=Operation.VIEW, description="View any role")
    add(
        scope=Scope.COLLABORATION,
        operation=Operation.VIEW,
        description="View any role in your collaborations",
    )
    add(
        scope=Scope.ORGANIZATION,
        operation=Operation.VIEW,
        description="View the roles of your organization",
    )
    add(
        scope=Scope.GLOBAL,
        operation=Operation.CREATE,
        description="Create role for any organization",
    )
    add(
        scope=Scope.COLLABORATION,
        operation=Operation.CREATE,
        description="Create role for any organization in your collaborations",
    )
    add(
        scope=Scope.ORGANIZATION,
        operation=Operation.CREATE,
        description="Create role for your organization",
    )
    add(scope=Scope.GLOBAL, operation=Operation.EDIT, description="Edit any role")
    add(
        scope=Scope.COLLABORATION,
        operation=Operation.EDIT,
        description="Edit any role in your collaborations",
    )
    add(
        scope=Scope.ORGANIZATION,
        operation=Operation.EDIT,
        description="Edit a role from your organization",
    )
    add(
        scope=Scope.GLOBAL,
        operation=Operation.DELETE,
        description="Delete a role from any organization",
    )
    add(
        scope=Scope.COLLABORATION,
        operation=Operation.DELETE,
        description="Delete a role from any organization in your collaborations",
    )
    add(
        scope=Scope.ORGANIZATION,
        operation=Operation.DELETE,
        description="Delete a role from your organization",
    )


# -----------------------------------------------------------------------------
# Resources / API's
# -----------------------------------------------------------------------------
role_schema = RoleSchema()
rule_schema = RuleSchema()
role_input_schema = ServerRoleInputSchema(default_roles=DefaultRole.list())


class RoleBase(ServicesResources):
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.rule_collection: RuleCollection = getattr(self.permissions, module_name)

    def _get_organization_id(self, data):
        return data.get("organization_id", g.user.organization_id)

    def _validate_organization(self, organization_id):
        if not db.Organization.get(organization_id):
            raise NotFoundError(f'Organization "{organization_id}" does not exist!')

    def _validate_user_permission(self, operation, organization_id):
        if not self.rule_collection.allowed_for_org(operation, organization_id):
            raise UnauthorizedError(
                f"You lack the permission to {operation} roles for organization {organization_id}!"
            )


class Roles(RoleBase):
    def _filter_by_organization(self, query, args):
        org_filters = args.getlist("organization_id")
        if org_filters:
            for org_id in org_filters:
                if not self.rule_collection.allowed_for_org(P.VIEW, org_id):
                    raise UnauthorizedError(
                        f"You lack the permission to view roles from organization {org_id}!"
                    )
            include_root = args.get("include_root", False)
            query = query.filter(
                or_(
                    db.Role.organization_id.in_(org_filters),
                    db.Role.organization_id.is_(None) if include_root else False,
                )
            )
        return query

    def _filter_by_collaboration(self, query, args):
        if "collaboration_id" in args:
            if not self.rule_collection.can_for_col(P.VIEW, args["collaboration_id"]):
                raise UnauthorizedError(
                    f"You lack the permission to view roles from collaboration {args['collaboration_id']}!"
                )
            org_ids = get_org_ids_from_collabs(g.user, args["collaboration_id"])
            include_root = args.get("include_root", False)
            query = query.filter(
                or_(
                    db.Role.organization_id.in_(org_ids),
                    db.Role.organization_id.is_(None) if include_root else False,
                )
            )
        return query

    def _filter_by_rule(self, query, args):
        if "rule_id" in args:
            get_rule(db, args["rule_id"])
            query = (
                query.join(db.role_rule_association)
                .join(db.Rule)
                .filter(db.Rule.id == args["rule_id"])
            )
        return query

    def _filter_by_user(self, query, args):
        if "user_id" in args:
            user = validate_user_exists(db, args["user_id"])
            if (
                not self.rule_collection.allowed_for_org(P.VIEW, user.organization_id)
                and not g.user.id == user.id
            ):
                raise UnauthorizedError(
                    f"You lack the permission to view roles from the organization that user id={user.id} belongs to!"
                )
            query = apply_user_filter(db, query, args["user_id"])
        return query

    def _filter_by_user_permissions(self, query, auth_org):
        own_role_ids = [role.id for role in g.user.roles]
        if self.rule_collection.v_col.can():
            query = query.filter(
                or_(
                    db.Role.id.in_(own_role_ids),
                    db.Role.organization_id.is_(None),
                    db.Role.organization_id.in_(
                        [
                            org.id
                            for col in self.obtain_auth_collaborations()
                            for org in col.organizations
                        ]
                    ),
                )
            )
        elif self.rule_collection.v_org.can():
            query = query.filter(
                or_(
                    db.Role.organization_id == auth_org.id,
                    db.Role.id.in_(own_role_ids),
                    db.Role.organization_id.is_(None),
                )
            )
        else:
            query = query.filter(db.Role.id.in_(own_role_ids))
        return query

    @with_user
    @handle_exceptions
    def get(self):
        """Returns a list of roles
        ---

        description: >-
            Returns a list of roles. Depending on your permission, you get all
            the roles at the server or only the roles that belong to your
            organization.\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Role|Global|View|❌|❌|View all roles|\n
            |Role|Collaboration|View|❌|❌|View all roles in your
            collaborations|\n
            |Role|Organization|View|❌|❌|View roles that are part of your
            organization|\n

            Accesible to users.

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
              name: description
              schema:
                type: string
              description: >-
                Description to match with a LIKE operator. \n
                * The percent sign (%) represents zero, one, or multiple
                characters\n
                * underscore sign (_) represents one, single character
            - in: query
              name: organization_id
              schema:
                type: array
                items:
                  type: integer
                  description: Organization id of which you want to get roles
            - in: query
              name: collaboration_id
              schema:
              type: integer
              description: Collaboration id
            - in: query
              name: rule_id
              schema:
                type: integer
              description: Get roles that this role id is part of
            - in: query
              name: user_id
              schema:
                type: integer
              description: Get roles for this user id
            - in: query
              name: include_root
              schema:
                 type: boolean
              description: Whether or not to include root role (default=False)
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

        tags: ["Role"]
        """
        q = select(db.Role)

        auth_org = self.obtain_auth_organization()

        q = self._filter_by_organization(q, request.args)
        q = self._filter_by_collaboration(q, request.args)
        q = filter_by_attribute(db, ["name", "description"], q, request.args)
        q = self._filter_by_rule(q, request.args)
        q = self._filter_by_user(q, request.args)

        if not self.rule_collection.v_glo.can():
            q = self._filter_by_user_permissions(q, auth_org)

        page = Pagination.from_query(q, request, db.Role)
        return self.response(page, role_schema)

    @with_user
    @handle_exceptions
    def post(self):
        """Creates a new role.
        ---
        description: >-
          Create a new role. You can only assign rules that you own. You need
          permission to create roles, and you can only assign roles to other
          organizations if you have gobal permission.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Role|Global|Create|❌|❌|Create a role for any organization|\n
          |Role|Collaboration|Create|❌|❌|Create a role for organization in
          your collaborations|\n
          |Role|Organization|Create|❌|❌|Create a role for your organization|\n

          Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Human readable name for collaboration
                  description:
                    type: string
                    description: Human readable description of the role
                  rules:
                    type: array
                    items:
                      type: integer
                      description: Rule id's to assign to role
                  organization_id:
                    type: integer
                    description: Organization to which role is added. If you
                      are root user and want to create a role that will be
                      available to all organizations, leave this empty.

        responses:
          201:
            description: Created
          400:
            description: Non-allowed role name
          401:
            description: Unauthorized
          404:
            description: Organization or rule was not found

        security:
          - bearerAuth: []

        tags: ["Role"]
        """
        data = request.get_json()
        validate_request_body(role_input_schema, data)

        rules = get_rules(data, db)
        self.permissions.check_user_rules(rules)
        organization_id = self._get_organization_id(data)
        self._validate_organization(organization_id)
        self._validate_user_permission(P.CREATE, organization_id)

        role = db.Role(
            name=data.get("name"),
            description=data.get("description"),
            rules=rules,
            organization_id=organization_id,
        )
        role.save()

        return role_schema.dump(role, many=False), HTTPStatus.CREATED


class Role(RoleBase):
    def has_permission_to_view(self, role) -> bool:
        return (
            self.rule_collection.allowed_for_org(P.VIEW, role.organization_id)
            or role in g.user.roles
            or (
                role.name in DefaultRole.list()
                and self.rule_collection.has_at_least_scope(Scope.ORGANIZATION, P.VIEW)
            )
        )

    @with_user
    @handle_exceptions
    def get(self, id):
        """Get roles
        ---
        description: >-
          Get role based on role identifier.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Role|Global|View|❌|❌|View all roles|\n
          |Role|Collaboration|View|❌|❌|View all roles for your
          collaborations|\n
          |Role|Organization|View|❌|❌|View roles that are part of your
          organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
              minimum: 1
            description: Role id
            required: true

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Role"]
        """
        role = get_role(db, id)

        if not self.has_permission_to_view(role):
            raise UnauthorizedError("You do not have permission to view this role.")

        return role_schema.dump(role, many=False), HTTPStatus.OK

    @with_user
    @handle_exceptions
    def patch(self, id):
        """Update role
        ---
        description: >-
          Updates roles if the user has permission to do so.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Role|Global|Edit|❌|❌|Update any role|\n
          |Role|Collaboration|Edit|❌|❌|Update any role in your
          collaborations|\n
          |Role|Organization|Edit|❌|❌|Update a role from your organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
              minimum: 1
            description: Role id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Human readable name for collaboration
                  description:
                    type: string
                    description: Human readable description of the role
                  rules:
                    type: array
                    items:
                      type: integer
                      description: Rule id's to assign to role

        responses:
          200:
            description: Ok
          400:
            description: Non-allowed role name change
          401:
            description: Unauthorized
          404:
            description: Role id or rule id not found

        security:
          - bearerAuth: []

        tags: ["Role"]
        """
        data = request.get_json()
        validate_request_body(role_input_schema, data, partial=True)

        if "organization_id" in data:
            raise BadRequestError("Cannot change role's organization")

        role = get_role(db, id)
        check_default_role(role, DefaultRole.list())
        self._validate_user_permission(P.EDIT, role.organization_id)
        role = update_role(role, data, db, self.permissions)
        role.save()

        return role_schema.dump(role, many=False), HTTPStatus.OK

    @with_user
    @handle_exceptions
    def delete(self, id):
        """Delete role
        ---
        description: >-
          Delete role from an organization if user is allowed to delete the
          role.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Role|Global|Delete|❌|❌|Delete any role|\n
          |Role|Collaboration|Delete|❌|❌|Delete any role in your
          collaborations|\n
          |Role|Organization|Delete|❌|❌|Delete a role in your organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
              minimum: 1
            description: Role id
            required: true
          - in: query
            name: delete_dependents
            schema:
              type: boolean
            description: If set to true, the role is deleted even though users
               with this role may lose permissions (default=False)

        responses:
          200:
            description: Ok
          400:
            description: Cannot delete default roles
          401:
            description: Unauthorized
          404:
            description: Role id not found

        security:
          - bearerAuth: []

        tags: ["Role"]
        """
        role = get_role(db, id)
        check_default_role(role, DefaultRole.list())
        self._validate_user_permission(P.DELETE, role.organization_id)
        can_delete_dependents(role, request.args.get("delete_dependents", False))
        role.delete()

        return {"msg": "Role removed from the database."}, HTTPStatus.OK
