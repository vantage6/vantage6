# -*- coding: utf-8 -*-
import logging
import base64

from marshmallow import fields
from marshmallow_sqlalchemy import ModelSchema
from flask import url_for

from vantage6.server import db
from vantage6.common import logger_name
from vantage6.common.globals import STRING_ENCODING
from vantage6.server.model import Organization

log = logging.getLogger(logger_name(__name__))


class HATEOASModelSchema(ModelSchema):
    """Convert foreign-key fields to HATEOAS specification."""

    api = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # to one relationship
        setattr(self, "node", lambda obj: self.hateos("node", obj))
        setattr(self, "organization",
                lambda obj: self.hateos("organization", obj))
        setattr(self, "collaboration",
                lambda obj: self.hateos("collaboration", obj))
        setattr(self, "user", lambda obj: self.hateos("user", obj))
        setattr(self, "result", lambda obj: self.hateos("result", obj))
        setattr(self, "task", lambda obj: self.hateos("task", obj))
        setattr(self, "parent_",
                lambda obj: self.hateos("parent", obj, endpoint="task"))

        # to many relationship
        setattr(self, "nodes", lambda obj: self.hateos_list("node", obj))
        setattr(self, "organizations",
                lambda obj: self.hateos_list("organization", obj))
        setattr(self, "collaborations",
                lambda obj: self.hateos_list("collaboration", obj))
        setattr(self, "users", lambda obj: self.hateos_list("user", obj))
        setattr(self, "results", lambda obj: self.hateos_list("result", obj))
        setattr(self, "tasks", lambda obj: self.hateos_list("task", obj))
        setattr(self, "children",
                lambda obj: self.hateos_list(
                    "children",
                    obj,
                    plural="children",
                    endpoint="task"
                ))
        setattr(self, "rules", lambda obj: self.hateos_list("rule", obj))
        setattr(self, "roles", lambda obj: self.hateos_list("role", obj))

        # special cases

    def many_hateos_from_secondary(self, first, second, obj):
        hateos_list = list()
        for elem in getattr(obj, first):
            hateos_list.append(
                self._hateos_from_related(getattr(elem, second), second)
            )
        return hateos_list

    def hateos_from_secondairy_model(self, first, second, obj):
        first_elem = getattr(obj, first)
        second_elem = getattr(first_elem, second)
        return self._hateos_from_related(second_elem, second)

    def hateos(self, name, obj, endpoint=None):
        elem = getattr(obj, name)
        endpoint = endpoint if endpoint else name
        if elem:
            return self._hateos_from_related(elem, endpoint)
        else:
            return None

    def hateos_list(self, name, obj, plural=None, endpoint=None):
        hateos_list = list()
        plural_ = plural if plural else name+"s"
        endpoint = endpoint if endpoint else name
        # FIXME 2022-04-14 this is a quick n dirty fix for making the endpoint
        # /organization/{id} faster by preventing it reads all columns from
        # all the organization's results.
        # THIS SHOULD NEVER MAKE IT INTO VERSION 3 AND HIGHER!!
        if isinstance(obj, Organization) and plural_ == 'results':
            elements = obj.get_result_ids()
        else:
            elements = getattr(obj, plural_)
        for elem in elements:
            hateos = self._hateos_from_related(elem, endpoint)
            hateos_list.append(hateos)

        if hateos_list:
            return hateos_list
        else:
            return None

    def _hateos_from_related(self, elem, name):
        _id = elem.id
        endpoint = name+"_with_id"
        if self.api:
            if not self.api.owns_endpoint(endpoint):
                Exception(f"Make sure {endpoint} exists!")

            verbs = list(
                self.api.app.url_map._rules_by_endpoint[endpoint][0].methods
            )
            verbs.remove("HEAD")
            verbs.remove("OPTIONS")
            url = url_for(endpoint, id=_id)
            return {"id": _id, "link": url, "methods": verbs}
        else:
            log.error("No API found?")


# /task/{id}
class TaskSchema(HATEOASModelSchema):
    class Meta:
        model = db.Task

    complete = fields.Boolean()
    collaboration = fields.Method("collaboration")
    results = fields.Method("results")
    parent = fields.Method("parent_")
    children = fields.Method("children")


# /task/{id}?include=result
class TaskIncludedSchema(TaskSchema):
    """Returns the TaskSchema plus the correspoding results."""
    results = fields.Nested('TaskResultSchema', many=True, exclude=['task'])


# /task/{id}/result
class TaskResultSchema(HATEOASModelSchema):
    class Meta:
        model = db.Result


class ResultSchema(HATEOASModelSchema):
    class Meta:
        model = db.Result

    organization = fields.Method("organization")
    task = fields.Method("task")


class ResultTaskIncludedSchema(ResultSchema):
    task = fields.Nested('TaskSchema', many=False, exclude=["results"])


class OrganizationSchema(HATEOASModelSchema):
    class Meta:
        model = db.Organization
        exclude = ('_public_key',)

    # convert fk to HATEOAS
    collaborations = fields.Method("collaborations")
    nodes = fields.Method("nodes")
    users = fields.Method("users")
    created_tasks = fields.Method("tasks")
    results = fields.Method("results")

    # make sure
    public_key = fields.Function(
        lambda obj: (
            base64.b64encode(obj._public_key).decode(STRING_ENCODING)
            if obj._public_key else ""
        )
    )


class CollaborationSchema(HATEOASModelSchema):
    class Meta:
        model = db.Collaboration

    # convert fk to HATEOAS
    organizations = fields.Method("organizations")
    nodes = fields.Method("nodes")
    tasks = fields.Method("tasks")


# ------------------------------------------------------------------------------
class CollaborationSchemaSimple(HATEOASModelSchema):

    nodes = fields.Nested(
        'NodeSchemaSimple',
        many=True,
        exclude=['nodes', 'tasks', 'collaboration']
    )

    class Meta:
        table = db.Collaboration.__table__
        exclude = [
            'tasks',
            'organizations',
            # 'nodes',
        ]


# ------------------------------------------------------------------------------
class NodeSchema(HATEOASModelSchema):
    # organization = ma.HyperlinkRelated('organization_with_id')
    # collaboration = ma.HyperlinkRelated('collaboration_with_id')

    organization = fields.Method("organization")
    collaboration = fields.Method("collaboration")

    class Meta:
        model = db.Node


# ------------------------------------------------------------------------------
class NodeSchemaSimple(HATEOASModelSchema):

    # collaboration = fields.Nested(
    #     'CollaborationSchema',
    #     many=False,
    #     exclude=['organizations', 'nodes', 'tasks']
    # )

    # organization = fields.Nested(
    #     'OrganizationSchema',
    #     many=False,
    #     exclude=[
    #         '_id',
    #         'id',
    #         'domain',
    #         'address1',
    #         'address2',
    #         'zipcode',
    #         'country',
    #         'nodes',
    #         'collaborations',
    #         'users',
    #         'results'
    #         ]
    # )
    organization = fields.Method("organization")

    class Meta:
        model = db.Node
        exclude = [
            # 'id',
            # 'organization',
            'collaboration',
            'taskresults',
            'api_key',
            'type',
        ]


# ------------------------------------------------------------------------------
class UserSchema(HATEOASModelSchema):

    class Meta:
        model = db.User
        exclude = ('password',)

    roles = fields.Method("roles")
    rules = fields.Method("rules")
    organization = fields.Method("organization")


# ------------------------------------------------------------------------------
class RoleSchema(HATEOASModelSchema):

    rules = fields.Method("rules")
    users = fields.Method("users")
    organization = fields.Method("organization")

    class Meta:
        model = db.Role


# ------------------------------------------------------------------------------
class RuleSchema(HATEOASModelSchema):

    scope = fields.Function(func=lambda obj: obj.scope.name)
    operation = fields.Function(func=lambda obj: obj.operation.name)
    roles = fields.Method("roles")
    users = fields.Method("users")

    class Meta:
        model = db.Rule
