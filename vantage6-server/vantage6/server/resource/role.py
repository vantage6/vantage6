# -*- coding: utf-8 -*-
import logging

from http import HTTPStatus
from flask.globals import request
from flask import g
from flask_restful import reqparse
from sqlalchemy import or_

from vantage6.server import db
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.resource import (
    with_user,
    ServicesResources
)
from vantage6.common import logger_name
from vantage6.server.permission import (
    PermissionManager
)
from vantage6.server.model.rule import Operation, Scope
from vantage6.server.resource._schema import RoleSchema, RuleSchema
from vantage6.server.resource.pagination import Pagination

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Roles,
        path,
        endpoint='role_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
    )
    api.add_resource(
        Role,
        path + '/<int:id>',
        endpoint="role_with_id",
        methods=('GET', 'PATCH', 'DELETE'),
        resource_class_kwargs=services
    )
    api.add_resource(
        RoleRules,
        path + '/<int:id>/rule',
        endpoint='role_rule_without_id',
        methods=('GET',),
        resource_class_kwargs=services
    )
    api.add_resource(
        RoleRules,
        path + '/<int:id>/rule/<int:rule_id>',
        endpoint='role_rule_with_id',
        methods=('DELETE', 'POST'),
        resource_class_kwargs=services
    )


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permission: PermissionManager):
    add = permission.appender(module_name)
    add(scope=Scope.GLOBAL, operation=Operation.VIEW,
        description="View any role")
    add(scope=Scope.ORGANIZATION, operation=Operation.VIEW,
        description="View the roles of your organization")
    add(scope=Scope.GLOBAL, operation=Operation.CREATE,
        description="Create role for any organization")
    add(scope=Scope.ORGANIZATION, operation=Operation.CREATE,
        description="Create role for your organization")
    add(scope=Scope.GLOBAL, operation=Operation.EDIT,
        description="Edit any role")
    add(scope=Scope.ORGANIZATION, operation=Operation.EDIT,
        description="Edit a role from your organization")
    add(scope=Scope.GLOBAL, operation=Operation.DELETE,
        description="Delete any organization")
    add(scope=Scope.ORGANIZATION, operation=Operation.DELETE,
        description="Delete your organization")


# -----------------------------------------------------------------------------
# Resources / API's
# -----------------------------------------------------------------------------
role_schema = RoleSchema()
rule_schema = RuleSchema()


class RoleBase(ServicesResources):

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)


class Roles(RoleBase):

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
              name: rule_id
              schema:
                type: integer
              description: Rule that is part of a role
            - in: query
              name: user_id
              schema:
                type: integer
              description: get roles for this user id
            - in: query
              name: include_root
              schema:
                 type: boolean
              description: Whether or not to include root role
            - in: query
              name: include
              schema:
                type: string (can be multiple)
              description: Include 'metadata' to get pagination metadata. Note
                that this will put the actual data in an envelope.
            - in: query
              name: page
              schema:
                type: integer
              description: Page number for pagination
            - in: query
              name: per_page
              schema:
                type: integer
              description: Number of items per page

        responses:
            200:
                description: Ok
            401:
                description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["Role"]
        """
        q = DatabaseSessionManager.get_session().query(db.Role)

        auth_org_id = self.obtain_organization_id()
        args = request.args

        # filter by organization ids (include root role if desired)
        org_filters = args.getlist('organization_id')
        if org_filters:
            if 'include_root' in args and args['include_root']:
                q = q.filter(or_(
                    db.Role.organization_id.in_(org_filters),
                    db.Role.organization_id == None
                ))
            else:
                q = q.filter(db.Role.organization_id.in_(org_filters))

        # filter by one or more names or descriptions
        for param in ['name', 'description']:
            filters = args.getlist(param)
            if filters:
                q = q.filter(or_(*[
                    getattr(db.Role, param).like(f) for f in filters
                ]))

        # find roles containing a specific rule
        if 'rule_id' in args:
            q = q.join(db.role_rule_association).join(db.Rule)\
                 .filter(db.Rule.id == args['rule_id'])

        if 'user_id' in args:
            q = q.join(db.Permission).join(db.User)\
                 .filter(db.User.id == args['user_id'])

        if not self.r.v_glo.can():
            own_role_ids = [role.id for role in g.user.roles]
            if self.r.v_org.can():
                # allow user to view all roles of their organization and any
                # other roles they may have themselves, or default roles from
                # the root organization
                q = q.filter(or_(
                        db.Role.organization_id == auth_org_id,
                        db.Role.id.in_(own_role_ids),
                        db.Role.organization_id == None
                    ))
            else:
                # allow users without permission to view only their own roles
                q = q.filter(db.Role.id.in_(own_role_ids))

        page = Pagination.from_query(query=q, request=request)

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
          404:
            description: Organization or rule was not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Role"]
        """
        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str, required=True)
        parser.add_argument("description", type=str, required=True)
        parser.add_argument("rules", type=int, action='append', required=False)
        parser.add_argument("organization_id", type=int, required=False)
        data = parser.parse_args()

        # obtain the requested rules from the DB.
        rules = []
        if data['rules']:
            for rule_id in data["rules"]:
                rule = db.Rule.get(rule_id)
                if not rule:
                    return {"msg": f"Rule id={rule_id} not found."}, \
                        HTTPStatus.NOT_FOUND
                rules.append(rule)

        # And check that this used has the rules he is trying to assign
        denied = self.permissions.verify_user_rules(rules)
        if denied:
            return denied, HTTPStatus.UNAUTHORIZED

        # set the organization id
        organization_id = (
            data['organization_id']
            if data['organization_id'] else g.user.organization_id
        )
        # verify that the organization for which we create a role exists
        if not db.Organization.get(organization_id):
            return {'msg': f'organization "{organization_id}" does not '
                    'exist!'}, HTTPStatus.NOT_FOUND

        # check if user is allowed to create this role
        if (not self.r.c_glo.can() and
                organization_id != g.user.organization_id):
            return {
                'msg': 'You cannot create roles for other organizations!'
            }, HTTPStatus.UNAUTHORIZED
        elif not self.r.c_glo.can() and not self.r.c_org.can():
            return {'msg': 'You lack the permission to create roles!'}, \
                HTTPStatus.UNAUTHORIZED

        # create the actual role
        role = db.Role(name=data["name"], description=data["description"],
                       rules=rules, organization_id=organization_id)
        role.save()

        return role_schema.dump(role, many=False).data, HTTPStatus.CREATED


class Role(RoleBase):

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
            return {"msg": f"Role with id={id} not found."}, \
                HTTPStatus.NOT_FOUND

        # check permissions. A user can always view their own roles
        if not (self.r.v_glo.can() or role in g.user.roles):
            if not (self.r.v_org.can()
                    and role.organization == g.user.organization):
                return {"msg": "You do not have permission to view this."},\
                     HTTPStatus.UNAUTHORIZED

        return role_schema.dump(role, many=False).data, HTTPStatus.OK

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
          401:
            description: Unauthorized
          404:
            description: Role id or rule id not found

        security:
          - bearerAuth: []

        tags: ["Role"]
        """
        data = request.get_json()

        role = db.Role.get(id)
        if not role:
            return {"msg": f"Role with id={id} not found."}, \
                HTTPStatus.NOT_FOUND

        # check permission of the user
        if not self.r.e_glo.can():
            if not self.r.e_org.can():
                return {'msg': 'You do not have permission to edit roles!'}, \
                    HTTPStatus.UNAUTHORIZED
            elif g.user.organization_id != role.organization.id:
                return {'msg': 'You can\'t edit roles from another '
                        'organization'}, HTTPStatus.UNAUTHORIZED

        # process patch
        if 'name' in data:
            role.name = data["name"]
        if 'description' in data:
            role.description = data["description"]
        if 'rules' in data:
            rules = []
            for rule_id in data['rules']:
                rule = db.Rule.get(rule_id)
                if not rule:
                    return {'msg': f'rule with id={rule_id} not found!'}, \
                        HTTPStatus.NOT_FOUND
                rules.append(rule)
            denied = self.permissions.verify_user_rules(rules)
            if denied:
                return denied, HTTPStatus.UNAUTHORIZED
            role.rules = rules
        role.save()

        return role_schema.dump(role, many=False).data, HTTPStatus.OK

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

        responses:
          200:
            description: Ok
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
            return {"msg": f"Role with id={id} not found."}, \
                HTTPStatus.NOT_FOUND

        if not self.r.d_glo.can():
            if not self.r.d_org.can():
                return {'msg': 'You do not have permission to delete roles!'},\
                    HTTPStatus.UNAUTHORIZED
            elif role.organization.id != g.user.organization.id:
                return {'msg': 'You can\'t delete a role from another '
                        'organization'}, HTTPStatus.UNAUTHORIZED

        role.delete()

        return {"msg": "Role removed from the database."}, HTTPStatus.OK


class RoleRules(RoleBase):

    @with_user
    def get(self, id):
        """Returns the rules for a specific role
        ---
        description: >-
            View the rules that belong to a specific role.\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Role|Global|View|❌|❌|View a role's rules|\n
            |Role|Organization|View|❌|❌|View a role's rules for roles in
            your organization|\n

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
              name: include
              schema:
                type: string (can be multiple)
              description: Include 'metadata' to get pagination metadata. Note
                that this will put the actual data in an envelope.
            - in: query
              name: page
              schema:
                type: integer
              description: Page number for pagination
            - in: query
              name: per_page
              schema:
                type: integer
              description: Number of items per page

        responses:
            200:
                description: Ok
            404:
                description: Node with specified id is not found
            401:
                description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["Role"]
        """
        role = db.Role.get(id)

        if not role:
            return {'msg': f'Role id={id} not found!'}, HTTPStatus.NOT_FOUND

        # obtain auth organization model
        auth_org = self.obtain_auth_organization()

        # check permission
        if not self.r.v_glo.can():
            if not (self.r.v_org.can() and auth_org == role.organization):
                return {'msg': 'You lack permissions to do that'}, \
                    HTTPStatus.UNAUTHORIZED

        # paginate elements
        page = Pagination.from_list(role.rules, request)

        return self.response(page, rule_schema)

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
            return {'msg': f'Role id={id} not found!'}, HTTPStatus.NOT_FOUND
        rule = db.Rule.get(rule_id)
        if not rule:
            return {'msg': f'Rule id={rule_id} not found!'}, \
                HTTPStatus.NOT_FOUND

        # check that this user can edit rules
        if not self.r.e_glo.can():
            if not (self.r.e_org.can() and
                    g.user.organization == role.organization):
                return {'msg': 'You lack permissions to do that'}, \
                    HTTPStatus.UNAUTHORIZED

        # user needs to role to assign it
        denied = self.permissions.verify_user_rules([rule])
        if denied:
            return denied, HTTPStatus.UNAUTHORIZED

        # We're good, lets add the rule
        role.rules.append(rule)
        role.save()

        return rule_schema.dump(role.rules, many=False).data, \
            HTTPStatus.CREATED

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
          |Role|Global|Delete|❌|❌|Delete any role rule|\n
          |Role|Organization|Delete|❌|❌|Delete any role rule in your
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
            return {'msg': f'Role id={id} not found!'}, HTTPStatus.NOT_FOUND
        rule = db.Rule.get(rule_id)
        if not rule:
            return {'msg': f'Rule id={rule_id} not found!'}, \
                HTTPStatus.NOT_FOUND

        if not self.r.d_glo.can():
            if not (self.r.d_org.can() and
                    g.user.organization == role.organization):
                return {'msg': 'You lack permissions to do that'}, \
                    HTTPStatus.UNAUTHORIZED

        # user needs to role to remove it
        denied = self.permissions.verify_user_rules([rule])
        if denied:
            return denied, HTTPStatus.UNAUTHORIZED

        if not (rule in role.rules):
            return {'msg': f'Rule id={rule_id} not found in Role={id}!'}, \
                HTTPStatus.NOT_FOUND

        # Ok jumped all hoopes, remove it..
        role.rules.remove(rule)

        return rule_schema.dump(role.rules, many=False).data, \
            HTTPStatus.OK
