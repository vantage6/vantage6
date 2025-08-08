import re

from marshmallow import Schema, ValidationError, fields, validates, validates_schema
from marshmallow.validate import Length, OneOf, Range

from vantage6.common.enum import AlgorithmStepType, RunStatus
from vantage6.common.globals import DEFAULT_API_PATH, SESSION_STATE_FILENAME

from vantage6.backend.common.resource.input_schema import (
    MAX_LEN_NAME,
    MAX_LEN_STR_LONG,
    validate_name,
)

from vantage6.server.dataclass import CreateTaskDB
from vantage6.server.model.common.utils import validate_password
from vantage6.server.model.rule import Scope

_MAX_LEN_STR_SHORT = 128


def _validate_username(username: str) -> None:
    """
    Validate a username field in the request input.

    Parameters
    ----------
    username : str
        Username to validate.

    Raises
    ------
    ValidationError
        If the username is empty, too long or numerical
    """
    validate_name(username)
    username_regex = r"^[a-zA-Z][a-zA-Z0-9._-]+$"
    if re.match(username_regex, username) is None:
        raise ValidationError(
            f"Username {username} is invalid. Only letters, numbers, hyphens and "
            "underscores are allowed, and it should start with a letter."
        )


def _validate_password(password: str) -> None:
    """
    Check if the password is strong enough.

    Parameters
    ----------
    password : str
        Password to validate.

    Raises
    ------
    ValidationError
        If the password is not strong enough.
    """
    try:
        validate_password(password)
    except ValueError as e:
        raise ValidationError(str(e))


def _validate_organization_ids(organization_ids: list[int]) -> None:
    """
    Validate the organization ids in the input.

    Parameters
    ----------
    organization_ids : list[int]
        List of organization ids to validate.

    Raises
    ------
    ValidationError
        If the organization ids are not valid.
    """
    if not all(i > 0 for i in organization_ids):
        raise ValidationError("Organization ids must be greater than 0")
    if not len(organization_ids) == len(set(organization_ids)):
        raise ValidationError("Organization ids must be unique")
    if not len(organization_ids):
        raise ValidationError("At least one organization id is required")


def _validate_organizations(organizations: list[dict]) -> None:
    """
    Validate the organizations in the input.

    Parameters
    ----------
    organizations : list[dict]
        List of organizations to validate. Each organization must have at
        least an organization id.

    Raises
    ------
    ValidationError
        If the organizations are not valid.
    """
    if not len(organizations):
        raise ValidationError("At least one organization is required")
    for organization in organizations:
        if "id" not in organization:
            raise ValidationError("Organization id is required for each organization")


class _OnlyIdSchema(Schema):
    """Schema for validating POST requests that only require an ID field."""

    id = fields.Integer(required=True, validate=Range(min=1))


class _NameValidationSchema(Schema):
    """Schema for validating POST requests with a name field."""

    name = fields.String(required=True)

    @validates("name")
    def validate_name(self, name: str):
        """
        Validate the name in the input.

        Parameters
        ----------
        name : str
            Name to validate.

        Raises
        ------
        ValidationError
            If the name is empty, too long or numerical
        """
        validate_name(name)


class CollaborationInputSchema(_NameValidationSchema):
    """Schema for validating input for a creating a collaboration."""

    organization_ids = fields.List(fields.Integer(), required=True)
    encrypted = fields.Boolean(required=True)
    session_restrict_to_same_image = fields.Boolean(load_default=0)

    @validates("organization_ids")
    def validate_organization_ids(self, organization_ids):
        """
        Validate the organization ids in the input.

        Parameters
        ----------
        organization_ids : list[int]
            List of organization ids to validate.

        Raises
        ------
        ValidationError
            If the organization ids are not valid.
        """
        _validate_organization_ids(organization_ids)


class CollaborationChangeOrganizationSchema(_OnlyIdSchema):
    """
    Schema for validating requests that add an organization to a collaboration.
    """

    pass


class CollaborationAddNodeSchema(_OnlyIdSchema):
    """Schema for validating requests that add a node to a collaboration."""

    pass


class KillTaskInputSchema(_OnlyIdSchema):
    """Schema for validating input for killing a task."""

    pass


class KillNodeTasksInputSchema(_OnlyIdSchema):
    """Schema for validating input for killing tasks on a node."""

    pass


class NodeInputSchema(_NameValidationSchema):
    """Schema for validating input for a creating a node."""

    # overwrite name attr as it is not required for a node
    name = fields.String(required=False)
    collaboration_id = fields.Integer(required=True, validate=Range(min=1))
    organization_id = fields.Integer(validate=Range(min=1))


class OrganizationInputSchema(_NameValidationSchema):
    """Schema for validating input for a creating an organization."""

    address1 = fields.String(validate=Length(max=_MAX_LEN_STR_SHORT))
    address2 = fields.String(validate=Length(max=_MAX_LEN_STR_SHORT))
    zipcode = fields.String(validate=Length(max=_MAX_LEN_STR_SHORT))
    country = fields.String(validate=Length(max=_MAX_LEN_STR_SHORT))
    domain = fields.String(validate=Length(max=_MAX_LEN_STR_SHORT))
    public_key = fields.String()


class ResetAPIKeyInputSchema(_OnlyIdSchema):
    """Schema for validating input for resetting an API key."""

    pass


class RunInputSchema(Schema):
    """Schema for validating input for patching an algorithm run."""

    started_at = fields.DateTime()
    finished_at = fields.DateTime()
    log = fields.String()
    result = fields.String()
    status = fields.String(validate=OneOf(RunStatus.list()))


class TaskInputSchema(_NameValidationSchema):
    """Schema for validating input for creating a task."""

    # overwrite name attr as it is not required for a task
    name = fields.String()
    description = fields.String(validate=Length(max=MAX_LEN_STR_LONG))
    image = fields.String(required=True, validate=Length(min=1))
    method = fields.String(required=True)
    collaboration_id = fields.Integer(validate=Range(min=1))
    study_id = fields.Integer(validate=Range(min=1))
    store_id = fields.Integer(validate=Range(min=1))
    depends_on_ids = fields.List(
        fields.Integer(validate=Range(min=1), required=False), load_default=[]
    )
    organizations = fields.List(fields.Dict(), required=True)
    databases = fields.List(fields.List(fields.Dict()), allow_none=True)
    session_id = fields.Integer(validate=Range(min=1), required=True)
    dataframe_id = fields.Integer(validate=Range(min=1))
    action = fields.String(validate=OneOf(AlgorithmStepType.list()))

    @validates_schema
    def validate_schema(self, data: dict, **kwargs) -> None:
        """
        Validate the input, which should contain a collaboration_id or a study_id. The
        input may also contain both.

        Parameters
        ----------
        data : dict
            The input data.

        Raises
        ------
        ValidationError
            If the input does not contain a collaboration_id or a study_id.
        """
        if not ("collaboration_id" in data or "study_id" in data):
            raise ValidationError("Collaboration_id or study_id is required")

    @validates("organizations")
    def validate_organizations(self, organizations: list[dict]):
        _validate_organizations(organizations)

    @validates("databases")
    def validate_databases(self, databases: list[list[dict]] | None):
        """
        Validate the databases in the input.

        Parameters
        ----------
        databases : list[list[dict]] | None
            List of databases to validate. Each database must have at least a database
            label or dataframe_id.

        Raises
        ------
        ValidationError
            If the databases are not valid.
        """
        if databases is None:
            return  # some algorithms don't use any database

        if isinstance(databases, list) and not isinstance(databases[0], list):
            raise ValidationError(
                "Databases must be a list of lists of dictionaries or None"
            )

        # create task database objects. This will raise validation errors if the
        # databases are not valid.
        # pylint: disable=expression-not-assigned
        [CreateTaskDB.from_dict(db) for sublist in databases for db in sublist]


class TokenAlgorithmInputSchema(Schema):
    """Schema for validating input for creating a token for an algorithm."""

    task_id = fields.Integer(required=True, validate=Range(min=1))
    image = fields.String(required=True, validate=Length(min=1))


class UserInputSchema(Schema):
    """Schema for validating input for creating a user."""

    username = fields.String(required=True, validate=Length(min=3, max=MAX_LEN_NAME))
    password = fields.String()
    organization_id = fields.Integer(validate=Range(min=1))
    roles = fields.List(fields.Integer(validate=Range(min=1)))
    rules = fields.List(fields.Integer(validate=Range(min=1)))
    is_service_account = fields.Boolean(required=False, load_default=False)

    @validates("username")
    def validate_username(self, username: str):
        """
        Check if the username is appropriate

        Parameters
        ----------
        username : str
            Username to validate.

        Raises
        ------
        ValidationError
            If the username is too short, too long or numeric.
        """
        _validate_username(username)

    @validates("password")
    def _validate_password(self, password: str):
        """
        Check if the password is strong enough.

        Parameters
        ----------
        password : str
            Password to validate.

        Raises
        ------
        ValidationError
            If the password is not strong enough.
        """
        _validate_password(password)


class UserEditInputSchema(UserInputSchema):
    """Schema for validating input for editing a user."""

    class Meta:
        fields = ("roles", "rules")


class DeleteDependentsInputSchema(Schema):
    """Schema for validating input for deleting a user or node with dependents."""

    delete_dependents = fields.Boolean()


class UserDeleteInputSchema(DeleteDependentsInputSchema):
    """Schema for validating input for deleting a user."""

    pass


class NodeDeleteInputSchema(DeleteDependentsInputSchema):
    """Schema for validating input for deleting a node."""

    pass


class ColumnNameInputSchema(Schema):
    """Schema for validating input for collecting database column names."""

    db_label = fields.String(required=True)
    collaboration_id = fields.Integer(required=True, validate=Range(min=1))
    organizations = fields.List(fields.Dict(), required=True)
    sheet_name = fields.String(required=False)
    query = fields.String(required=False)

    @validates("organizations")
    def validate_organizations(self, organizations: list[dict]):
        _validate_organizations(organizations)


class AlgorithmStoreInputSchema(Schema):
    """Schema for validating input for creating an algorithm store."""

    name = fields.String(required=True)
    algorithm_store_url = fields.Url(required=True)
    api_path = fields.String(required=False, load_default=DEFAULT_API_PATH)
    collaboration_id = fields.Integer(validate=Range(min=1))


class StudyInputSchema(_NameValidationSchema):
    """Schema for validating input for creating a study"""

    collaboration_id = fields.Integer(required=True, validate=Range(min=1))
    organization_ids = fields.List(fields.Integer(), required=True)

    @validates("organization_ids")
    def validate_organization_ids(self, organization_ids):
        """
        Validate the organization ids in the input.

        Parameters
        ----------
        organization_ids : list[int]
            List of organization ids to validate.

        Raises
        ------
        ValidationError
            If the organization ids are not valid.
        """
        _validate_organization_ids(organization_ids)


class StudyChangeOrganizationSchema(_OnlyIdSchema):
    """
    Schema for validating requests that add an organization to a study.
    """

    pass


class SessionTaskInputSchema(Schema):
    """Schema for validating input for creating a session task."""

    image = fields.String(required=True)
    store_id = fields.Integer(validate=Range(min=1))
    method = fields.String(required=True)

    # This is a list of dictionaries, where each dictionary contains the
    # organization id and the organization's data extraction input (optional).
    organizations = fields.List(fields.Dict(), required=True)

    @validates("organizations")
    def validate_organizations(self, organizations: list[dict]):
        _validate_organizations(organizations)


class SessionInputSchema(Schema):
    """Schema for validating input for creating a session."""

    # Used to identify the session
    name = fields.String(allow_none=True)

    collaboration_id = fields.Integer(required=True, validate=Range(min=1))
    study_id = fields.Integer(validate=Range(min=1), allow_none=True)
    scope = fields.String(required=True, dump_default=Scope.OWN.value)

    @validates("scope")
    def validate_scope(self, scope: str):
        """
        Validate the scope in the input.

        Parameters
        ----------
        scope : str
            Scope to validate.

        Raises
        ------
        ValidationError
            If the scope is not valid.
        """
        allowed_scopes = set(Scope.names()) - {Scope.GLOBAL.name.lower()}
        if scope not in allowed_scopes:
            raise ValidationError(
                f"Session scope '{scope}' is not valid. Allowed values are: "
                f"{allowed_scopes}."
            )


class DataframeInitInputSchema(Schema):
    """Schema for validating input for creating a new dataframe in a session."""

    # Databse label that is specified in the node configuration file
    label = fields.String(required=True)

    # Name that can be used in within the session
    name = fields.String()

    # Task metadata that is executed on the node for session initialization, which is
    # the data extraction task
    task = fields.Nested(SessionTaskInputSchema, required=True)

    @validates("name")
    def validate_name(self, name: str):
        """
        Validate the name in the input.
        """
        # Check that the name does not contain special characters or spaces, hyphens
        # and underscores are allowed. We need to be safe as this name is used as the
        # filename on the nodes. And ',' and ';' have special meaning in the
        # environment variables.
        if not re.match(r"^[a-zA-Z0-9-_]+$", name):
            raise ValidationError(
                "Dataframe name must contain only letters, numbers, hyphens and "
                "underscores"
            )
        if name == SESSION_STATE_FILENAME:
            raise ValidationError(
                f"Dataframe name cannot be '{SESSION_STATE_FILENAME}'. This name is "
                "reserved as it is used to track the status of the session."
            )


class DataframePreprocessingInputSchema(Schema):
    """
    Schema for validating input for creating a new dataframe preprocessing step in
    a session.
    """

    dataframe_id = fields.Integer(required=True, validate=Range(min=1))

    # Task metadata that is executed on the node for session extension, which is a
    # pre-processing task
    task = fields.Nested(SessionTaskInputSchema, required=True)


class DataframeNodeUpdateSchema(Schema):
    """Schema for validating input for updating the column names"""

    name = fields.String(required=True)
    dtype = fields.String(required=True)
