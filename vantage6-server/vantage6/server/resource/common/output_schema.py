import logging
import base64

from marshmallow import fields
from flask import url_for

from vantage6.server import db
from vantage6.common import logger_name
from vantage6.common.globals import STRING_ENCODING
from vantage6.server.model import Base, User
from vantage6.backend.common.resource.output_schema import BaseHATEOASModelSchema

log = logging.getLogger(logger_name(__name__))


def create_one_to_many_link(obj: Base, link_to: str, link_from: str) -> str:
    """
    Create an API link to get objects related to a given object.

    Parameters
    ----------
    obj : Base
        Object to which the link is created
    link_to : str
        Name of the resource to which the link is created
    link_from : str
        Name of the resource from which the link is created

    Returns
    -------
    str
        API link

    Examples
    --------
    >>> create_one_to_many_link(obj, "node", "organization_id")
    "/api/node?organization_id=<obj.id>"
    """
    endpoint = link_to + "_without_id"
    values = {link_from: obj.id}
    return url_for(endpoint, **values)


class HATEOASModelSchema(BaseHATEOASModelSchema):
    """
    This class is used to convert foreign-key fields to HATEOAS specification.
    """

    def __init__(self, *args, **kwargs) -> None:
        # set lambda functions to create links for one to one relationship
        setattr(self, "node", lambda obj: self.create_hateoas("node", obj))
        setattr(
            self, "organization", lambda obj: self.create_hateoas("organization", obj)
        )
        setattr(
            self, "collaboration", lambda obj: self.create_hateoas("collaboration", obj)
        )
        setattr(self, "user", lambda obj: self.create_hateoas("user", obj))
        setattr(self, "run", lambda obj: self.create_hateoas("run", obj))
        setattr(self, "task", lambda obj: self.create_hateoas("task", obj))
        setattr(self, "port", lambda obj: self.create_hateoas("port", obj))
        setattr(
            self,
            "parent_",
            lambda obj: self.create_hateoas("parent", obj, endpoint="task"),
        )
        setattr(
            self,
            "init_org_",
            lambda obj: self.create_hateoas("init_org", obj, endpoint="organization"),
        )
        setattr(
            self,
            "init_user_",
            lambda obj: self.create_hateoas("init_user", obj, endpoint="user"),
        )
        setattr(self, "study", lambda obj: self.create_hateoas("study", obj))

        # call super class. Do this after setting the attributes above, because
        # the super class initializer will call the attributes.
        super().__init__(*args, **kwargs)


# /task/{id}
class TaskSchema(HATEOASModelSchema):
    class Meta:
        model = db.Task

    status = fields.String()
    finished_at = fields.DateTime()
    collaboration = fields.Method("collaboration")
    runs = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="run", link_from="task_id")
    )
    results = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="result", link_from="task_id")
    )
    parent = fields.Method("parent_")
    children = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="task", link_from="parent_id")
    )
    init_org = fields.Method("init_org_")
    init_user = fields.Method("init_user_")
    databases = fields.Method("databases_")
    study = fields.Method("study")

    @staticmethod
    def databases_(obj):
        return [
            {"label": db.database, "parameters": db.parameters} for db in obj.databases
        ]


class ResultSchema(HATEOASModelSchema):
    class Meta:
        model = db.Run
        exclude = (
            "assigned_at",
            "started_at",
            "finished_at",
            "status",
            "ports",
            "organization",
            "log",
            "input",
        )

    run = fields.Method("make_run_link")
    task = fields.Method("task")

    @staticmethod
    def make_run_link(obj):
        return {
            "id": obj.id,
            "link": url_for("run_with_id", id=obj.id),
            "methods": ["GET", "PATCH"],
        }


# /task/{id}?include=runs
class TaskWithRunSchema(TaskSchema):
    """Returns the TaskSchema plus the correspoding runs."""

    runs = fields.Nested("RunSchema", many=True)


# /task/{id}?include=results
class TaskWithResultSchema(TaskSchema):
    """Returns the TaskSchema plus the correspoding results."""

    results = fields.Nested("ResultSchema", many=True)


# /task/{id}?include=runs,results
class TaskWithRunAndResultSchema(TaskSchema):
    """Returns the TaskSchema plus the correspoding runs and results."""

    runs = fields.Nested("RunSchema", many=True)
    results = fields.Nested("ResultSchema", many=True)


class RunSchema(HATEOASModelSchema):
    class Meta:
        model = db.Run
        exclude = ("result",)

    organization = fields.Method("organization")
    task = fields.Method("task")
    results = fields.Method("result_link")
    node = fields.Function(
        serialize=lambda obj: RunNodeSchema().dump(obj.node, many=False)
    )
    ports = fields.Function(
        serialize=lambda obj: RunPortSchema().dump(obj.ports, many=True)
    )

    @staticmethod
    def result_link(obj):
        return {
            "id": obj.id,
            "link": url_for("result_with_id", id=obj.id),
            "methods": ["GET", "PATCH"],
        }


class RunTaskIncludedSchema(RunSchema):
    task = fields.Nested("TaskSchema", many=False, exclude=["runs"])


class RunNodeSchema(HATEOASModelSchema):
    class Meta:
        model = db.Node
        exclude = ("type", "api_key", "collaboration", "organization", "last_seen")


class PortSchema(HATEOASModelSchema):
    class Meta:
        model = db.AlgorithmPort


class RunPortSchema(HATEOASModelSchema):
    class Meta:
        model = db.AlgorithmPort
        exclude = ("run",)


class OrganizationSchema(HATEOASModelSchema):
    class Meta:
        model = db.Organization
        exclude = ("_public_key",)

    # add links to linked resources
    collaborations = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="collaboration", link_from="organization_id"
        )
    )
    nodes = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="node", link_from="organization_id"
        )
    )
    users = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="user", link_from="organization_id"
        )
    )
    tasks = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="task", link_from="init_org_id"
        )
    )
    runs = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="run", link_from="organization_id"
        )
    )
    studies = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="study", link_from="organization_id"
        )
    )

    public_key = fields.Function(
        lambda obj: (
            base64.b64encode(obj._public_key).decode(STRING_ENCODING)
            if obj._public_key
            else ""
        )
    )


class CollaborationSchema(HATEOASModelSchema):
    class Meta:
        model = db.Collaboration

    # add links to linked resources
    organizations = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="organization", link_from="collaboration_id"
        )
    )
    nodes = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="node", link_from="collaboration_id"
        )
    )
    tasks = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="task", link_from="collaboration_id"
        )
    )
    algorithm_stores = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="algorithm_store", link_from="collaboration_id"
        )
    )
    studies = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="study", link_from="collaboration_id"
        )
    )


class CollaborationWithOrgsSchema(CollaborationSchema):
    """
    Returns the CollaborationSchema plus the organizations participating in it.
    """

    organizations = fields.Nested("OrganizationSchema", many=True)


class StudySchema(HATEOASModelSchema):
    class Meta:
        model = db.Study

    collaboration = fields.Method("collaboration")
    organizations = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="organization", link_from="study_id"
        )
    )
    tasks = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="task", link_from="study_id")
    )


class StudyWithOrgsSchema(StudySchema):
    """
    Returns the StudySchema plus the organizations participating in it.
    """

    organizations = fields.Nested("OrganizationSchema", many=True)


class NodeSchema(HATEOASModelSchema):
    organization = fields.Method("organization")
    collaboration = fields.Method("collaboration")
    config = fields.Nested("NodeConfigSchema", many=True, exclude=["id"])

    class Meta:
        model = db.Node
        exclude = ("api_key",)


class NodeConfigSchema(HATEOASModelSchema):
    class Meta:
        model = db.NodeConfig


class NodeSchemaSimple(HATEOASModelSchema):
    organization = fields.Method("organization")

    class Meta:
        model = db.Node
        exclude = (
            "collaboration",
            "api_key",
            "type",
        )


class AlgorithmStoreSchema(HATEOASModelSchema):
    class Meta:
        model = db.AlgorithmStore

    collaborations = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="collaboration", link_from="algorithm_store_id"
        )
    )


class UserSchema(HATEOASModelSchema):
    class Meta:
        model = db.User
        exclude = ("password", "failed_login_attempts", "last_login_attempt")

    roles = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="role", link_from="user_id")
    )
    rules = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="rule", link_from="user_id")
    )

    organization = fields.Method("organization")


class UserWithPermissionDetailsSchema(UserSchema):
    """
    A schema for API responses that contains regular user details plus
    additional permission details for the user to be used by the UI.
    """

    permissions = fields.Method("permissions_")

    @staticmethod
    def permissions_(obj: User) -> dict:
        """
        Returns a dictionary containing permission details for the user to be
        used by the UI.

        Parameters
        ----------
        obj : User
            The user to get permission details for.

        Returns
        -------
        dict
            A dictionary containing permission details for the user.
        """
        role_ids = [role.id for role in obj.roles]
        rule_ids = list(
            set(
                [rule.id for rule in obj.rules]
                + [rule.id for role in obj.roles for rule in role.rules]
            )
        )
        # Return which organizations the user is in collaboration with so that
        # UI knows which organizations user has access to if they have
        # collaboration scope permissions
        orgs_in_collabs = list(
            set(
                [
                    org.id
                    for collab in obj.organization.collaborations
                    for org in collab.organizations
                ]
            )
        )
        return {
            "roles": role_ids,
            "rules": rule_ids,
            "orgs_in_collabs": orgs_in_collabs,
        }


class RoleSchema(HATEOASModelSchema):
    rules = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="rule", link_from="role_id")
    )
    users = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="user", link_from="role_id")
    )
    organization = fields.Method("organization")

    class Meta:
        model = db.Role


class RuleSchema(HATEOASModelSchema):
    scope = fields.Function(serialize=lambda obj: obj.scope.name)
    operation = fields.Function(serialize=lambda obj: obj.operation.name)
    users = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="user", link_from="rule_id")
    )

    class Meta:
        model = db.Rule
        exclude = ("roles",)
