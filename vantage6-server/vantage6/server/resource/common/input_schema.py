from marshmallow import (
    Schema, fields, ValidationError, validates, validates_schema
)
from marshmallow.validate import Length, Range


class _OnlyIdSchema(Schema):
    """ Schema for validating POST requests that only require an ID field. """
    id = fields.Integer(required=True, validate=Range(min=1))


class CollaborationInputSchema(Schema):
    """ Schema for validating input for a creating a collaboration. """
    name = fields.String(required=True, validate=Length(max=128))
    organization_ids = fields.List(fields.Integer(), required=True)
    encrypted = fields.Boolean(required=True)

    @validates('organization_ids')
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
        if not all(i > 0 for i in organization_ids):
            raise ValidationError('Organization ids must be greater than 0')
        if not len(organization_ids) == len(set(organization_ids)):
            raise ValidationError('Organization ids must be unique')
        if not len(organization_ids):
            raise ValidationError('At least one organization id is required')


class CollaborationAddOrganizationSchema(_OnlyIdSchema):
    """
    Schema for validating requests that add an organization to a collaboration.
    """
    pass


class CollaborationAddNodeSchema(_OnlyIdSchema):
    """ Schema for validating requests that add a node to a collaboration. """
    pass


class KillTaskInputSchema(_OnlyIdSchema):
    """ Schema for validating input for killing a task. """
    pass


class KillNodeTasksInputSchema(_OnlyIdSchema):
    """ Schema for validating input for killing tasks on a node. """
    pass


class NodeInputSchema(Schema):
    """ Schema for validating input for a creating a node. """
    name = fields.String(validate=Length(max=128))
    collaboration_id = fields.Integer(required=True, validate=Range(min=1))
    organization_id = fields.Integer(validate=Range(min=1))


class OrganizationInputSchema(Schema):
    """ Schema for validating input for a creating an organization. """
    name = fields.String(required=True, validate=Length(max=128))
    address1 = fields.String(validate=Length(max=128))
    address2 = fields.String(validate=Length(max=128))
    zipcode = fields.String(validate=Length(max=128))
    country = fields.String(validate=Length(max=128))
    domain = fields.String(validate=Length(max=128))
    public_key = fields.String(validate=Length(max=128))


class PortInputSchema(Schema):
    """ Schema for validating input for a creating a port. """
    port = fields.Integer(required=True)
    run_id = fields.Integer(required=True, validate=Range(min=1))
    label = fields.String(validate=Length(max=128))

    @validates('port')
    def validate_port(self, port):
        """
        Validate the port in the input.

        Parameters
        ----------
        port : int
            Port to validate.

        Raises
        ------
        ValidationError
            If the port is not valid.
        """
        if not 1 <= port <= 65535:
            raise ValidationError('Port must be between 1 and 65535')


class RecoverPasswordInputSchema(Schema):
    """ Schema for validating input for recovering a password. """
    email = fields.Email(validate=Length(max=256))
    username = fields.String(validate=Length(max=128))

    @validates_schema
    def validate_email_or_username(self, data, **kwargs):
        if not ('email' in data or 'username' in data):
            raise ValidationError('Email or username is required')


class ResetPasswordInputSchema(Schema):
    """ Schema for validating input for resetting a password. """
    reset_token = fields.String(required=True, validate=Length(max=512))
    password = fields.String(required=True, validate=Length(max=128))


class Recover2FAInputSchema(Schema):
    """ Schema for validating input for recovering 2FA. """
    email = fields.Email(validate=Length(max=256))
    username = fields.String(validate=Length(max=128))
    password = fields.String(validate=Length(max=128))

    @validates_schema
    def validate_email_or_username(self, data, **kwargs):
        if not ('email' in data or 'username' in data):
            raise ValidationError('Email or username is required')


class Reset2FAInputSchema(Schema):
    """ Schema for validating input for resetting 2FA. """
    reset_token = fields.String(required=True, validate=Length(max=512))


class ResetAPIKeyInputSchema(_OnlyIdSchema):
    """ Schema for validating input for resetting an API key. """
    pass


class RoleInputSchema(Schema):
    """ Schema for validating input for creating a role. """
    name = fields.String(required=True, validate=Length(max=128))
    description = fields.String(validate=Length(max=512))
    rules = fields.List(fields.Integer(validate=Range(min=1)), required=True)
    organization_id = fields.Integer(validate=Range(min=1))


class TaskInputSchema(Schema):
    """ Schema for validating input for creating a task. """
    name = fields.String(validate=Length(max=128))
    description = fields.String(validate=Length(max=512))
    image = fields.String(required=True, validate=Length(max=1024))
    collaboration_id = fields.Integer(required=True, validate=Range(min=1))
    organizations = fields.List(fields.Dict(), required=True)
    databases = fields.List(fields.String())

    @validates('organizations')
    def validate_organizations(self, organizations):
        """
        Validate the organizations in the input.

        Parameters
        ----------
        """
        if not len(organizations):
            raise ValidationError('At least one organization is required')
        for organization in organizations:
            if 'id' not in organization:
                raise ValidationError(
                    'Organization id is required for each organization')
            if 'input' not in organization:
                raise ValidationError(
                    'Input is required for each organization')


class UserInputSchema(Schema):
    """ Schema for validating input for creating a user. """
    username = fields.String(required=True, validate=Length(max=128))
    email = fields.Email(required=True, validate=Length(max=256))
    # TODO use the checks from user.set_password() to validate proper password
    # also in other places in this file
    password = fields.String(required=True, validate=Length(max=128))
    firstname = fields.String(validate=Length(max=128))
    lastname = fields.String(validate=Length(max=128))
    organization_id = fields.Integer(validate=Range(min=1))
    roles = fields.List(fields.Integer(validate=Range(min=1)))
    rules = fields.List(fields.Integer(validate=Range(min=1)))


class VPNConfigUpdateInputSchema(Schema):
    """ Schema for validating input for updating a VPN configuration. """
    vpn_config = fields.String(required=True)
