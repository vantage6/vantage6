import logging

from flask import request, g
from flask_restful import Api
from http import HTTPStatus
from marshmallow import ValidationError
from sqlalchemy import select

from vantage6.server import db
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.server.resource.common.input_schema import (
    StudyChangeOrganizationSchema,
    StudyInputSchema,
)
from vantage6.server.permission import (
    RuleCollection,
    Scope as S,
    Operation as P,
    PermissionManager,
)
from vantage6.server.resource.common.output_schema import (
    OrganizationSchema,
    StudySchema,
    StudyWithOrgsSchema,
)
from vantage6.server.resource import with_user, only_for, ServicesResources


module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the study resource.

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
    log.info('Setting up "%s" and subdirectories', path)

    api.add_resource(
        Studies,
        path,
        endpoint="study_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Study,
        path + "/<int:id>",
        endpoint="study_with_id",
        methods=("GET", "PATCH", "DELETE"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        StudyOrganization,
        path + "/<int:id>/organization",
        endpoint="study_with_id_organization",
        methods=("POST", "DELETE"),
        resource_class_kwargs=services,
    )


# # Schemas
study_schema = StudySchema()
org_schema = OrganizationSchema()
study_with_orgs_schema = StudyWithOrgsSchema()
study_input_schema = StudyInputSchema()
study_change_org_schema = StudyChangeOrganizationSchema()


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

    add(scope=S.GLOBAL, operation=P.VIEW, description="view any study")
    add(
        scope=S.ORGANIZATION,
        operation=P.VIEW,
        assign_to_container=True,
        assign_to_node=True,
        description="view studies that your organization is involved in",
    )
    add(
        scope=S.COLLABORATION,
        operation=P.VIEW,
        description="view studies within your collaborations",
    )
    add(scope=S.GLOBAL, operation=P.EDIT, description="edit any study")
    add(
        scope=S.COLLABORATION,
        operation=P.EDIT,
        description="edit studies within your collaborations",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.EDIT,
        description="edit studies that your organization is involved in",
    )

    add(scope=S.GLOBAL, operation=P.CREATE, description="create a new study")
    add(
        scope=S.COLLABORATION,
        operation=P.CREATE,
        description="create a new study within your collaborations",
    )

    add(scope=S.GLOBAL, operation=P.DELETE, description="delete a study")
    add(
        scope=S.COLLABORATION,
        operation=P.DELETE,
        description="delete any study within your collaborations",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.DELETE,
        description="delete studies that your organization is involved in",
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class StudyBase(ServicesResources):
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)

    def _select_schema(self) -> StudySchema:
        """
        Select the output schema based on which resources should be included

        Returns
        -------
        StudySchema or derivative of it
            Schema to use for serialization
        """
        if self.is_included("organizations"):
            return study_with_orgs_schema
        else:
            return study_schema

    def _check_membership_collaboration(
        self, organization_ids: list[int], collaboration_id: int
    ) -> bool:
        """
        Check whether organizations are all members of a collaboration

        Parameters
        ----------
        organization_ids : list[int]
            List of organization ids
        collaboration_id : int
            Collaboration id

        Returns
        -------
        bool
            True if all organizations are members of the collaboration, False otherwise
        """
        collab = db.Collaboration.get(collaboration_id)
        return set(organization_ids).issubset(
            set([org.id for org in collab.organizations])
        )


class Studies(StudyBase):
    """Resource for /api/study."""

    @only_for(("user", "node"))
    def get(self):
        """Returns a list of studies, which are subsets of organizations from a
        collaboration
        ---
        description: >-
          Returns a list of studies. Depending on your permission, all
          studies are shown or only studies in which your organization participates.
          See the table bellow.\n\n

          ### Permission Table\n
          |Rulename|Scope|Operation|Assigned to Node|Assigned to Container|
          Description|\n
          | -- | -- | -- | -- | -- | -- |\n
          |Study|Global|View|❌|❌|All studies|\n
          |Study|Collaboration|View|❌|❌|Studies which are part of collaborations
          that your organization participates in|\n
          |Study|Organization|View|✅|✅|Studies in which
          your organization participates |\n\n

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
            name: organization_id
            schema:
              type: integer
            description: Filter studies by organization id
          - in: query
            name: collaboration_id
            schema:
              type: integer
            description: Filter studies by collaboration id
          - in: query
            name: include
            schema:
              type: array
              items:
                type: string
            description: Include 'organizations' to include the organizations
              in the output.
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

        tags: ["Collaboration"]
        """

        # obtain organization from authenticated
        auth_org_id = self.obtain_organization_id()
        auth_collab_ids = self.obtain_auth_collaboration_ids()
        args = request.args
        q = select(db.Study)

        # filter by a field of this endpoint
        if "name" in args:
            q = q.filter(db.Study.name.like(args["name"]))

        # find studies containing a specific organization
        if "organization_id" in args:
            if self.r.v_glo.can() or self.r.v_col.can():
                # find all studies containing the organization. Note that for the
                # collaboration scope, we filter by collaboration later on
                q = (
                    q.join(db.StudyMember)
                    .join(db.Organization)
                    .filter(db.Organization.id == args["organization_id"])
                )
            elif self.r.v_org.can() and args["organization_id"] == str(auth_org_id):
                # the user can already only view filters of their own organization, so
                # argument is superfluous: no additional filters necessary
                pass
            else:
                return {
                    "msg": "You lack the permission to request studies for this "
                    "organization!"
                }, HTTPStatus.UNAUTHORIZED

        # Note that the collaboration_id filter is not allowed in most endpoints if the
        # user only has organization permission - in those cases they will often
        # unknowingly miss part of the resources. Here it is allowed because there is a
        # clear use case: the user wants to see all their studies
        if "collaboration_id" in args:
            if self.r.v_glo.can() or (
                (self.r.v_col.can() or self.r.v_org.can())
                and int(args["collaboration_id"]) in auth_collab_ids
            ):
                q = q.filter(db.Study.collaboration_id == args["collaboration_id"])
            else:
                return {
                    "msg": "You lack the permission to request studies for this "
                    "collaboration!"
                }, HTTPStatus.UNAUTHORIZED

        # filter based on permissions
        if not self.r.v_glo.can():
            if self.r.v_col.can():
                q = q.join(
                    db.Collaboration,
                    db.Study.collaboration_id == db.Collaboration.id,
                ).filter(db.Collaboration.id.in_(auth_collab_ids))
            elif self.r.v_org.can():
                q = q.join(db.Organization, db.Study.organizations).filter(
                    db.Study.organizations.any(id=auth_org_id)
                )
            else:
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        # paginate the results
        try:
            page = Pagination.from_query(q, request, db.Study)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        schema = self._select_schema()

        # serialize models
        return self.response(page, schema)

    @with_user
    def post(self):
        """Create study
        ---
        description: >-
          Create a new study between organizations.\n\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to Node|Assigned to
          Container|Description|\n
          |--|--|--|--|--|--|\n
          |Study|Global|Create|❌|❌|Create study in any collaboration|\n\n
          |Study|Collaboration|Create|❌|❌|Create study in collaborations that your
          organization participates in|\n\n

          Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Unique human readable name for the study
                  collaboration_id:
                    type: integer
                    description: Collaboration id to which the study belongs
                  organization_ids:
                    type: array
                    items:
                      type: integer
                      description: List of organization ids which form the
                        study

        responses:
          200:
            description: Ok
          400:
            description: Study name already exists, or not all organizations are member
              of the collaboration
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        data = request.get_json(silent=True)
        # validate request body
        try:
            data = study_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        name = data["name"]
        if db.Study.exists("name", name):
            return {
                "msg": f"Study with name '{name}' already exists!"
            }, HTTPStatus.BAD_REQUEST

        if not self.r.can_for_col(P.CREATE, data["collaboration_id"]):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        organizations_in_collab = self._check_membership_collaboration(
            data["organization_ids"], data["collaboration_id"]
        )
        if not organizations_in_collab:
            return {
                "msg": "Not all organizations are part of the collaboration!"
            }, HTTPStatus.BAD_REQUEST

        study = db.Study(
            name=name,
            collaboration_id=data["collaboration_id"],
            organizations=[
                db.Organization.get(org_id)
                for org_id in data["organization_ids"]
                if db.Organization.get(org_id)
            ],
        )

        study.save()
        return study_with_orgs_schema.dump(study), HTTPStatus.CREATED


class Study(StudyBase):
    """Resource for /api/study/<int:id>."""

    @only_for(("user", "node", "container"))
    def get(self, id):
        """Get study
        ---
        description: >-
          Returns the study with the specified id.\n

          ### Permission Table\n
          |Rulename|Scope|Operation|Assigned to Node|Assigned to Container|
          Description|\n
          | -- | -- | -- | -- | -- | -- |\n
          |Study|Global|View|❌|❌|All studies|\n
          |Study|Collaboration|View|❌|❌|Studies which are part of collaborations
          that your organization participates in|\n
          |Study|Organization|View|✅|✅|Studies in which
          your organization participates |\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
              minimum: 1
            description: Study id
            required: true
          - in: query
            name: include
            schema:
              type: array
              items:
                type: string
            description: Include 'organizations' to include the organizations
              within the study.

        responses:
          200:
            description: Ok
          404:
            description: Study with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        study = db.Study.get(id)

        # check that study exists
        if not study:
            return {"msg": f"Study with id={id} not found"}, HTTPStatus.NOT_FOUND

        # obtain the organization id of the authenticated
        auth_org_id = self.obtain_organization_id()
        auth_collab_ids = self.obtain_auth_collaboration_ids()

        # verify that the right permissions are present
        org_ids = [org.id for org in study.organizations]
        if (
            not self.r.v_glo.can()
            and not (self.r.v_col.can() and study.collaboration_id in auth_collab_ids)
            and not (self.r.v_org.can() and auth_org_id in org_ids)
        ):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        schema = self._select_schema()

        return schema.dump(study, many=False), HTTPStatus.OK  # 200

    @with_user
    def patch(self, id):
        """Update study
        ---
        description: >-
          Updates the study with the specified id.\n\n
          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Study|Global|Edit|❌|❌|Update a study|\n
          |Study|Collaboration|Edit|❌|❌|Update a study within collaborations that
          your organization is a member of|\n\n
          |Study|Organization|Edit|❌|❌|Update a study that your organization is a
          member of|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Study id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Human readable label
                  organization_ids:
                    type: array
                    items:
                      type: integer
                    description: List of organization ids

        responses:
          200:
            description: Ok
          404:
            description: Study with specified id is not found
          401:
            description: Unauthorized
          400:
            description: Study name already exists, organizations are not
              collaboration members, or request body is incorrect

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        study = db.Study.get(id)

        # check if collaboration exists
        if not study:
            return {
                "msg": f"Study with id={id} can not be found"
            }, HTTPStatus.NOT_FOUND  # 404

        # verify permissions
        auth_org_id = self.obtain_organization_id()
        if (
            not self.r.e_glo.can()
            and not (
                self.r.e_col.can()
                and study.collaboration_id in self.obtain_auth_collaboration_ids()
            )
            and not (
                self.r.e_org.can()
                and auth_org_id in [org.id for org in study.organizations]
            )
        ):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        data = request.get_json(silent=True)
        # validate request body
        try:
            data = study_input_schema.load(data, partial=True)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # only update fields that are provided
        if "name" in data:
            name = data["name"]
            if study.name != name and db.Study.exists("name", name):
                return {
                    "msg": f"Study name '{name}' already exists!"
                }, HTTPStatus.BAD_REQUEST
            study.name = name
        if "organization_ids" in data:
            # check that all organizations are member of the collaboration
            organizations_in_collab = self._check_membership_collaboration(
                data["organization_ids"], study.collaboration_id
            )
            if not organizations_in_collab:
                return {
                    "msg": "Not all organizations are part of the collaboration!"
                }, HTTPStatus.BAD_REQUEST
            study.organizations = [
                db.Organization.get(org_id)
                for org_id in data["organization_ids"]
                if db.Organization.get(org_id)
            ]

        study.save()

        return (
            study_with_orgs_schema.dump(study, many=False),
            HTTPStatus.OK,
        )  # 200

    @with_user
    def delete(self, id):
        """Delete study
        ---
        description: >-
          Removes the study from the database entirely.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Study|Global|Delete|❌|❌|Remove study|\n
          |Study|Collaboration|Delete|❌|❌|Remove studies from collaborations that
          your organization is a member of|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Study id
            required: true
          - in: query
            name: delete_dependents
            schema:
              type: boolean
            description: If set to true, the study will be deleted along with all its
              tasks (default=False)

        responses:
          200:
            description: Ok
          404:
            description: Study with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """

        study = db.Study.get(id)
        if not study:
            return {"msg": f"Study with id={id} not found"}, HTTPStatus.NOT_FOUND

        # verify permissions
        if (
            not self.r.d_glo.can()
            and not (
                self.r.d_col.can()
                and study.collaboration_id in self.obtain_auth_collaboration_ids()
            )
            and not (
                self.r.d_org.can()
                and self.obtain_organization_id()
                in [org.id for org in study.organizations]
            )
        ):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        if study.tasks:
            delete_dependents = request.args.get("delete_dependents", False)
            if not delete_dependents:
                return {
                    "msg": f"Study id={id} has {len(study.tasks)} tasks. Please delete"
                    " them separately or set delete_dependents=True"
                }, HTTPStatus.BAD_REQUEST
            else:
                log.warning(
                    "Deleting study id=%s along with %s tasks",
                    id,
                    len(study.tasks),
                )
                for task in study.tasks:
                    task.delete()

        study.delete()
        return {"msg": f"Study id={id} successfully deleted"}, HTTPStatus.OK


class StudyOrganization(ServicesResources):
    """Resource for /api/study/<int:id>/organization."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)

    @with_user
    def post(self, id):
        """Add organization to study
        ---
        description: >-
          Adds a single organization to an existing study.\n\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Study|Global|Edit|❌|❌|Add organization to a study|\n
          |Study|Collaboration|Edit|❌|❌|Add organization to a study that your
          organization is already a member of|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Study id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  id:
                    type: integer
                    description: Organization id which needs to be added

        responses:
          200:
            description: Ok
          404:
            description: Specified study or organization does not exist
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        # get collaboration to which te organization should be added
        study = db.Study.get(id)
        if not study:
            return {"msg": f"Study with id={id} can not be found"}, HTTPStatus.NOT_FOUND

        # verify permissions
        if not self.r.can_for_col(P.EDIT, study.collaboration_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # validate request body
        data = request.get_json(silent=True)
        try:
            data = study_change_org_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # get the organization
        organization = db.Organization.get(data["id"])
        if not organization:
            return {
                "msg": f"organization with id={id} is not found"
            }, HTTPStatus.NOT_FOUND

        # check that organization is collaboration member
        if not organization in study.collaboration.organizations:
            return {
                "msg": "Organization is not a member of the collaboration!"
            }, HTTPStatus.BAD_REQUEST

        # append organization to the collaboration
        study.organizations.append(organization)
        study.save()
        return org_schema.dump(study.organizations, many=True), HTTPStatus.OK

    @with_user
    def delete(self, id):
        """Remove organization from a study
        ---
        description: >-
          Removes a single organization from an existing study.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Study|Global|Edit|❌|❌|Remove an organization from an
          existing study|\n
          |Study|Collaboration|Edit|❌|❌|Remove an organization from
          an existing study within collaborations that your organization is a member
          of|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Study id
            required: true

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  id:
                    type: integer
                    description: Organization id which needs to be deleted

        responses:
          200:
            description: Ok
          404:
            description: Specified collaboration or organization does not exist
          401:
            description: Unauthorized

        tags: ["Collaboration"]
        """
        # get collaboration from which organization should be removed
        study = db.Study.get(id)
        if not study:
            return {"msg": f"Study with id={id} can not be found"}, HTTPStatus.NOT_FOUND

        # validate requst body
        data = request.get_json(silent=True)
        try:
            data = study_change_org_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # get organization which should be deleted
        org_id = data["id"]
        organization = db.Organization.get(org_id)
        if not organization:
            return {
                "msg": f"Organization with id={org_id} is not found"
            }, HTTPStatus.NOT_FOUND

        if not self.r.can_for_col(P.EDIT, study.collaboration_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # delete organization and update
        study.organizations.remove(organization)
        study.save()
        return org_schema.dump(study.organizations, many=True), HTTPStatus.OK
