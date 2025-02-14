import logging

from http import HTTPStatus
from flask.globals import request
from flask import g
from flask_restful import Api
from sqlalchemy import or_

from vantage6.backend.common.input_schema import RoleInputSchema
from vantage6.backend.common.resource.role import get_rules
from vantage6.server import db
from vantage6.server.resource import (
    get_org_ids_from_collabs,
    with_user,
    ServicesResources,
)
from vantage6.common import logger_name
from vantage6.server.permission import (
    PermissionManager,
    RuleCollection,
    Operation as P,
)
from vantage6.server.model.rule import Operation, Scope
from vantage6.server.resource.common.output_schema import RoleSchema, RuleSchema
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.server.default_roles import DefaultRole

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
    api.add_resource(
        RoleRules,
        path + "/<int:id>/rule/<int:rule_id>",
        endpoint="role_rule_with_id",
        methods=("DELETE", "POST"),
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
        description="Delete a role from any organization in your " "collaborations",
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
role_input_schema = RoleInputSchema(default_roles=[role for role in DefaultRole])


def validate_request_body(schema, data, partial=False):
    errors = schema.validate(data, partial=partial)
    if errors:
        return {
            "msg": "Request body is incorrect",
            "errors": errors,
        }, HTTPStatus.BAD_REQUEST
    return None


class RoleBase(ServicesResources):
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)

    def check_permissions(self, rules):
        denied = self.permissions.check_user_rules(rules)
        if denied:
            return denied, HTTPStatus.UNAUTHORIZED
        return None

    def get_organization_id(self, data):
        return data.get("organization_id", g.user.organization_id)

    def validate_organization(self, organization_id):
        if not db.Organization.get(organization_id):
            return {
                "msg": f'Organization "{organization_id}" does not exist!'
            }, HTTPStatus.NOT_FOUND
        return None

    def validate_user_permission(self, operation, organization_id):
        if not self.r.allowed_for_org(operation, organization_id):
            return {
                "msg": "You do not have permission to perform this action!"
            }, HTTPStatus.UNAUTHORIZED
        return None


class Roles(RoleBase):
    def filter_by_organization(self, query, args):
        org_filters = args.getlist("organization_id")
        if org_filters:
            for org_id in org_filters:
                if not self.r.allowed_for_org(P.VIEW, org_id):
                    return {
                        "msg": f"You lack the permission to view roles from organization {org_id}!"
                    }, HTTPStatus.UNAUTHORIZED
            include_root = args.get("include_root", False)
            query = query.filter(
                or_(
                    db.Role.organization_id.in_(org_filters),
                    db.Role.organization_id.is_(None) if include_root else False,
                )
            )
        return query

    def filter_by_collaboration(self, query, args):
        if "collaboration_id" in args:
            if not self.r.can_for_col(P.VIEW, args["collaboration_id"]):
                return {
                    "msg": f"You lack the permission to view roles from collaboration {args['collaboration_id']}!"
                }, HTTPStatus.UNAUTHORIZED
            org_ids = get_org_ids_from_collabs(g.user, args["collaboration_id"])
            include_root = args.get("include_root", False)
            query = query.filter(
                or_(
                    db.Role.organization_id.in_(org_ids),
                    db.Role.organization_id.is_(None) if include_root else False,
                )
            )
        return query

    def filter_by_name_or_description(self, query, args):
        for param in ["name", "description"]:
            filters = args.getlist(param)
            if filters:
                query = query.filter(
                    or_(*[getattr(db.Role, param).like(f) for f in filters])
                )
        return query

    def filter_by_rule(self, query, args):
        if "rule_id" in args:
            rule = db.Rule.get(args["rule_id"])
            if not rule:
                return {
                    "msg": f'Rule with id={args["rule_id"]} does not exist!'
                }, HTTPStatus.BAD_REQUEST
            query = (
                query.join(db.role_rule_association)
                .join(db.Rule)
                .filter(db.Rule.id == args["rule_id"])
            )
        return query

    def filter_by_user(self, query, args):
        if "user_id" in args:
            user = db.User.get(args["user_id"])
            if not user:
                return {
                    "msg": f'User with id={args["user_id"]} does not exist!'
                }, HTTPStatus.BAD_REQUEST
            elif (
                not self.r.allowed_for_org(P.VIEW, user.organization_id)
                and not g.user.id == user.id
            ):
                return {
                    "msg": f"You lack the permission to view roles from the organization that user id={user.id} belongs to!"
                }, HTTPStatus.UNAUTHORIZED
            query = (
                query.join(db.Permission)
                .join(db.User)
                .filter(db.User.id == args["user_id"])
            )
        return query

    def filter_by_user_permissions(self, query, auth_org):
        own_role_ids = [role.id for role in g.user.roles]
        if self.r.v_col.can():
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
        elif self.r.v_org.can():
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
        q = g.session.query(db.Role)
        auth_org = self.obtain_auth_organization()
        args = request.args

        q = self.filter_by_organization(q, args)
        q = self.filter_by_collaboration(q, args)
        q = self.filter_by_name_or_description(q, args)
        q = self.filter_by_rule(q, args)
        q = self.filter_by_user(q, args)

        if not self.r.v_glo.can():
            q = self.filter_by_user_permissions(q, auth_org)

        try:
            page = Pagination.from_query(q, request, db.Role)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        return self.response(page, role_schema)

    @with_user
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
        validation_error = validate_request_body(role_input_schema, data)
        if validation_error:
            return validation_error

        rules = get_rules(data, db)
        denied = self.check_permissions(rules)
        if denied:
            return denied

        organization_id = self.get_organization_id(data)
        validation_error = self.validate_organization(organization_id)
        if validation_error:
            return validation_error

        permission_error = self.validate_user_permission(P.CREATE, organization_id)
        if permission_error:
            return permission_error

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
            self.r.allowed_for_org(P.VIEW, role.organization_id)
            or role in g.user.roles
            or (
                role.name in [role for role in DefaultRole]
                and self.r.has_at_least_scope(Scope.ORGANIZATION, P.VIEW)
            )
        )

    def update_role(self, role, data):
        if "name" in data:
            role.name = data["name"]
        if "description" in data:
            role.description = data["description"]
        if "rules" in data:
            rules = self.get_rules_from_ids(data["rules"])
            denied = self.permissions.check_user_rules(rules)
            if denied:
                return denied, HTTPStatus.UNAUTHORIZED
            role.rules = rules

    def get_rules_from_ids(self, rule_ids):
        rules = []
        for rule_id in rule_ids:
            rule = db.Rule.get(rule_id)
            if not rule:
                return {
                    "msg": f"rule with id={rule_id} not found!"
                }, HTTPStatus.NOT_FOUND
            rules.append(rule)
        return rules

    def can_delete_dependents(self):
        params = request.args
        if not params.get("delete_dependents", False):
            return False
        log.warn(
            f"Role {id} deleted even though it was assigned to users. This may result in missing permissions."
        )
        return True

    @with_user
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
        role = db.Role.get(id)

        if not role:
            return {"msg": f"Role with id={id} not found."}, HTTPStatus.NOT_FOUND

        if not self.has_permission_to_view(role):
            return {
                "msg": "You do not have permission to view this."
            }, HTTPStatus.UNAUTHORIZED

        return role_schema.dump(role, many=False), HTTPStatus.OK

    @with_user
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

        validation_error = validate_request_body(role_input_schema, data, partial=True)
        if validation_error:
            return validation_error

        if "organization_id" in data:
            return {
                "msg": "Cannot change organization of a role."
            }, HTTPStatus.BAD_REQUEST

        role = db.Role.get(id)
        if not role:
            return {"msg": f"Role with id={id} not found."}, HTTPStatus.NOT_FOUND

        if role.name in [role for role in DefaultRole]:
            return {
                "msg": f"This role ('{role.name}') is a default role. Its name cannot be changed."
            }, HTTPStatus.BAD_REQUEST

        if not self.r.allowed_for_org(P.EDIT, role.organization_id):
            return {
                "msg": "You do not have permission to edit this role!"
            }, HTTPStatus.UNAUTHORIZED

        self.update_role(role, data)
        role.save()

        return role_schema.dump(role, many=False), HTTPStatus.OK

    @with_user
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
        role = db.Role.get(id)
        if not role:
            return {"msg": f"Role with id={id} not found."}, HTTPStatus.NOT_FOUND

        if role.name in [role for role in DefaultRole]:
            return {
                "msg": f"This role ('{role.name}') is a default role. Default roles cannot be deleted."
            }, HTTPStatus.BAD_REQUEST

        if not self.r.allowed_for_org(P.DELETE, role.organization_id):
            return {
                "msg": "You do not have permission to delete this role!"
            }, HTTPStatus.UNAUTHORIZED

        if role.users and not self.can_delete_dependents():
            return {
                "msg": "Role is assigned to users. Please remove the role from the users first, or set the 'delete_dependents' parameter to delete the role anyway."
            }, HTTPStatus.BAD_REQUEST

        role.delete()
        return {"msg": "Role removed from the database."}, HTTPStatus.OK


class RoleRules(RoleBase):
    @with_user
    def post(self, id, rule_id):
        """Add a rule to a role.
        ---
        description: >-
          Add a rule to a role given that the role exists already and that the
          user has the permission to do so.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Role|Global|Edit|❌|❌|Edit any role|\n
          |Role|Collaboration|Edit|❌|❌|Edit any role in your collaborations
          |\n
          |Role|Organization|Edit|❌|❌|Edit any role in your organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Role id
            required: tr
          - in: path
            name: rule_id
            schema:
              type: integer
            description: Rule id to add to role
            required: tr

        responses:
          201:
            description: Added rule to role
          404:
            description: Rule or role not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Role"]
        """
        role = db.Role.get(id)
        if not role:
            return {"msg": f"Role id={id} not found!"}, HTTPStatus.NOT_FOUND

        rule = db.Rule.get(rule_id)
        if not rule:
            return {"msg": f"Rule id={rule_id} not found!"}, HTTPStatus.NOT_FOUND

        if not self.r.allowed_for_org(P.EDIT, role.organization_id):
            return {"msg": "You lack permissions to do that"}, HTTPStatus.UNAUTHORIZED

        denied = self.check_permissions([rule])
        if denied:
            return denied

        role.rules.append(rule)
        role.save()

        return rule_schema.dump(role.rules, many=True), HTTPStatus.CREATED

    @with_user
    def delete(self, id, rule_id):
        """Removes rule from role.
        ---
        description: >-
          Removes a rule from a role given the user has permission and the rule
          id exists.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Role|Global|Edit|❌|❌|Delete any rule in a role|\n
          |Role|Collaboration|Edit|❌|❌|Delete any rule in roles in your
          collaborations|\n
          |Role|Organization|Edit|❌|❌|Delete any rule in roles in your
          organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Role id
          - in: path
            name: rule_id
            schema:
              type: integer
            description: Rule id to delete from the role
            required: true

        responses:
          200:
            description: Ok
          404:
            description: Role or rule id not found
          401:
            description: Unauthorized

        tags: ["Role"]
        """
        role = db.Role.get(id)
        if not role:
            return {"msg": f"Role id={id} not found!"}, HTTPStatus.NOT_FOUND

        rule = db.Rule.get(rule_id)
        if not rule:
            return {"msg": f"Rule id={rule_id} not found!"}, HTTPStatus.NOT_FOUND

        if not self.r.allowed_for_org(P.EDIT, role.organization_id):
            return {"msg": "You lack permissions to do that"}, HTTPStatus.UNAUTHORIZED

        denied = self.check_permissions([rule])
        if denied:
            return denied

        if rule not in role.rules:
            return {
                "msg": f"Rule id={rule_id} not found in Role={id}!"
            }, HTTPStatus.NOT_FOUND

        role.rules.remove(rule)
        role.save()

        return rule_schema.dump(role.rules, many=True), HTTPStatus.OK
