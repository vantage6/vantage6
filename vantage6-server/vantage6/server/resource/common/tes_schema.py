"""
Marshmallow schemas for GA4GH Task Execution Service (TES) API.

These schemas define the input and output formats for the TES-compatible
API endpoints in vantage6.
"""
from marshmallow import Schema, fields, validate, EXCLUDE


TES_STATES = [
    "UNKNOWN",
    "QUEUED",
    "INITIALIZING",
    "RUNNING",
    "PAUSED",
    "COMPLETE",
    "EXECUTOR_ERROR",
    "SYSTEM_ERROR",
    "CANCELED",
    "CANCELING",
    "PREEMPTED",
]

TES_FILE_TYPES = ["FILE", "DIRECTORY"]


class TesInputSchema(Schema):
    """Schema for TES input files."""

    class Meta:
        unknown = EXCLUDE

    name = fields.String(load_default=None)
    description = fields.String(load_default=None)
    url = fields.String(load_default=None)
    path = fields.String(required=True)
    type = fields.String(
        load_default="FILE", validate=validate.OneOf(TES_FILE_TYPES)
    )
    content = fields.String(load_default=None)
    streamable = fields.Boolean(load_default=False)


class TesOutputSchema(Schema):
    """Schema for TES output files."""

    class Meta:
        unknown = EXCLUDE

    name = fields.String(load_default=None)
    description = fields.String(load_default=None)
    url = fields.String(required=True)
    path = fields.String(required=True)
    path_prefix = fields.String(load_default=None)
    type = fields.String(
        load_default="FILE", validate=validate.OneOf(TES_FILE_TYPES)
    )


class TesExecutorSchema(Schema):
    """Schema for TES executors (commands to run)."""

    class Meta:
        unknown = EXCLUDE

    image = fields.String(required=True)
    command = fields.List(fields.String(), required=True)
    workdir = fields.String(load_default=None)
    stdin = fields.String(load_default=None)
    stdout = fields.String(load_default=None)
    stderr = fields.String(load_default=None)
    env = fields.Dict(keys=fields.String(), values=fields.String(), load_default=None)
    ignore_error = fields.Boolean(load_default=False)


class TesResourcesSchema(Schema):
    """Schema for TES resource requirements."""

    class Meta:
        unknown = EXCLUDE

    cpu_cores = fields.Integer(load_default=None)
    ram_gb = fields.Float(load_default=None)
    disk_gb = fields.Float(load_default=None)
    preemptible = fields.Boolean(load_default=None)
    zones = fields.List(fields.String(), load_default=None)
    backend_parameters = fields.Dict(
        keys=fields.String(), values=fields.String(), load_default=None
    )
    backend_parameters_strict = fields.Boolean(load_default=False)


class TesExecutorLogSchema(Schema):
    """Schema for TES executor logs."""

    class Meta:
        unknown = EXCLUDE

    start_time = fields.String(load_default=None)
    end_time = fields.String(load_default=None)
    stdout = fields.String(load_default=None)
    stderr = fields.String(load_default=None)
    exit_code = fields.Integer(required=True)


class TesOutputFileLogSchema(Schema):
    """Schema for TES output file logs."""

    class Meta:
        unknown = EXCLUDE

    url = fields.String(required=True)
    path = fields.String(required=True)
    size_bytes = fields.String(load_default=None)


class TesTaskLogSchema(Schema):
    """Schema for TES task logs."""

    class Meta:
        unknown = EXCLUDE

    logs = fields.List(fields.Nested(TesExecutorLogSchema), load_default=None)
    metadata = fields.Dict(
        keys=fields.String(), values=fields.String(), load_default=None
    )
    start_time = fields.String(load_default=None)
    end_time = fields.String(load_default=None)
    outputs = fields.List(fields.Nested(TesOutputFileLogSchema), load_default=None)
    system_logs = fields.List(fields.String(), load_default=None)


class TesTaskInputSchema(Schema):
    """Schema for creating a TES task (input validation)."""

    class Meta:
        unknown = EXCLUDE

    name = fields.String(load_default=None)
    description = fields.String(load_default=None)
    inputs = fields.List(fields.Nested(TesInputSchema), load_default=None)
    outputs = fields.List(fields.Nested(TesOutputSchema), load_default=None)
    resources = fields.Nested(TesResourcesSchema, load_default=None)
    executors = fields.List(fields.Nested(TesExecutorSchema), required=True)
    volumes = fields.List(fields.String(), load_default=None)
    tags = fields.Dict(keys=fields.String(), values=fields.String(), load_default=None)


class TesTaskSchema(Schema):
    """Schema for TES task output (serialization)."""

    class Meta:
        unknown = EXCLUDE

    id = fields.String(dump_only=True)
    state = fields.String(
        dump_only=True, validate=validate.OneOf(TES_STATES)
    )
    name = fields.String(load_default=None)
    description = fields.String(load_default=None)
    inputs = fields.List(fields.Nested(TesInputSchema), load_default=None)
    outputs = fields.List(fields.Nested(TesOutputSchema), load_default=None)
    resources = fields.Nested(TesResourcesSchema, load_default=None)
    executors = fields.List(fields.Nested(TesExecutorSchema), load_default=None)
    volumes = fields.List(fields.String(), load_default=None)
    tags = fields.Dict(keys=fields.String(), values=fields.String(), load_default=None)
    logs = fields.List(fields.Nested(TesTaskLogSchema), dump_only=True, load_default=None)
    creation_time = fields.String(dump_only=True, load_default=None)


class TesCreateTaskResponseSchema(Schema):
    """Schema for TES create task response."""

    id = fields.String(required=True)


class TesListTasksResponseSchema(Schema):
    """Schema for TES list tasks response."""

    tasks = fields.List(fields.Nested(TesTaskSchema), required=True)
    next_page_token = fields.String(load_default=None)


class TesCancelTaskResponseSchema(Schema):
    """Schema for TES cancel task response (empty object)."""

    pass


class TesServiceTypeSchema(Schema):
    """Schema for TES service type."""

    group = fields.String(required=True)
    artifact = fields.String(required=True)
    version = fields.String(required=True)


class TesOrganizationSchema(Schema):
    """Schema for TES organization info."""

    name = fields.String(required=True)
    url = fields.String(required=True)


class TesServiceInfoSchema(Schema):
    """Schema for TES service info."""

    id = fields.String(required=True)
    name = fields.String(required=True)
    type = fields.Nested(TesServiceTypeSchema, required=True)
    description = fields.String(load_default=None)
    organization = fields.Nested(TesOrganizationSchema, load_default=None)
    contactUrl = fields.String(load_default=None)
    documentationUrl = fields.String(load_default=None)
    createdAt = fields.String(load_default=None)
    updatedAt = fields.String(load_default=None)
    environment = fields.String(load_default=None)
    version = fields.String(required=True)
    storage = fields.List(fields.String(), load_default=None)
    tesResources_backend_parameters = fields.List(fields.String(), load_default=None)
