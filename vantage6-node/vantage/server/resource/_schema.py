# -*- coding: utf-8 -*-
import logging
import base64

from marshmallow import fields
from marshmallow_sqlalchemy import (
    ModelSchema, 
    field_for, 
    ModelConverter
)
from flask import url_for, Flask
from flask_marshmallow.sqla import HyperlinkRelated
from flask_marshmallow import Schema
from marshmallow.fields import List, Integer
from werkzeug.routing import BuildError

from vantage.server import api
from vantage.util import logger_name
from vantage.constants import STRING_ENCODING
from .. import ma
from .. import db

log = logging.getLogger(logger_name(__name__))


class HATEOASModelSchema(ModelSchema):
    """Convert foreign-key fields to HATEOAS specification."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # to one relationship
        setattr(self, "node",
            lambda obj: self.hateos("node", obj))
        setattr(self, "organization",
            lambda obj: self.hateos("organization", obj))
        setattr(self, "collaboration",
            lambda obj: self.hateos("collaboration", obj))
        setattr(self, "user",
            lambda obj: self.hateos("user", obj))
        setattr(self, "result",
            lambda obj: self.hateos("result", obj))
        setattr(self, "task",
            lambda obj: self.hateos("task", obj))
        
        # to many relationship
        setattr(self, "nodes", 
            lambda obj: self.hateos_list("node", obj))
        setattr(self, "organizations", 
            lambda obj: self.hateos_list("organization", obj))
        setattr(self, "collaborations", 
            lambda obj: self.hateos_list("collaboration", obj))
        setattr(self, "users", 
            lambda obj: self.hateos_list("user", obj))
        setattr(self, "results", 
            lambda obj: self.hateos_list("result", obj))
        setattr(self, "tasks", 
            lambda obj: self.hateos_list("task", obj))

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

    def hateos(self, name, obj):
        elem = getattr(obj, name)
        return self._hateos_from_related(elem, name)
    
    def hateos_list(self, name, obj):
        hateos_list = list()
        type_ = type(obj)
        for elem in getattr(obj, name+"s"):
            hateos = self._hateos_from_related(elem, name)
            hateos_list.append(hateos)
        return hateos_list
    
    def _hateos_from_related(self, elem, name):
        _id = elem.id
        endpoint = name+"_with_id"
        if not api.owns_endpoint(endpoint):
            Exception(f"Make sure {endpoint} exists!")
        
        verbs = list(api.app.url_map._rules_by_endpoint[endpoint][0].methods)
        verbs.remove("HEAD")
        verbs.remove("OPTIONS")
        url = url_for(endpoint, id=_id)
        return {"id":_id, "link":url, "methods": verbs}


# /task/{id}
class TaskSchema(HATEOASModelSchema):
    class Meta:
        model = db.Task

    complete = fields.Boolean()
    collaboration = fields.Method("collaboration")
    results = fields.Method("results")


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
    tasks = fields.Method("tasks")
    
    # make sure 
    public_key = fields.Function(
        lambda self: base64.b64encode(self._public_key).decode(STRING_ENCODING) if \
            self._public_key else ""
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

    organization = fields.Nested(
        'OrganizationSchema', 
        many=False, 
        exclude=[
            '_id', 
            'id', 
            'domain', 
            'address1', 
            'address2', 
            'zipcode', 
            'country',
            'nodes', 
            'collaborations', 
            'users',
            ]
    )


    class Meta:
        model = db.Node
        exclude = [
            # 'id', 
            # 'organization', 
            # 'collaboration', 
            'taskresults', 
            'api_key', 
            'type', 
        ]

# ------------------------------------------------------------------------------
class UserSchema(HATEOASModelSchema):
    
    class Meta:
        model = db.User
        exclude = ('password',)

    organization = fields.Method("organization")