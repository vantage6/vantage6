# -*- coding: utf-8 -*-
from joey.server import api
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

from .. import ma
from .. import db

# class CustomModelConverter(ModelConverter):
    
#     def add_link_field(self, links):

class HATEOASModelSchema(ModelSchema):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # define HATEOAS methods for different entities
        setattr(self, "nodes", 
            lambda obj: self.hateos("node", obj))
        setattr(self, "organizations", 
            lambda obj: self.hateos("organization", obj))
        setattr(self, "collaborations", 
            lambda obj: self.hateos("collaboration", obj))
        setattr(self, "users", 
            lambda obj: self.hateos("user", obj))
        setattr(self, "results", 
            lambda obj: self.hateos("result", obj))
        setattr(self, "tasks", 
            lambda obj: self.hateos("task", obj))
        setattr(self, "task_assignments", 
            lambda obj: self.hateos("task_assignment", obj))
    
    def hateos(self, name, obj):
        hateos = list()
        for elem in getattr(obj, name+"s"):
            _id = elem.id
            endpoint = name+"_with_id"
            if not api.owns_endpoint(endpoint):
                Exception("Make sure <endpoint>_with_id exists!")
            
            verbs = list(api.app.url_map._rules_by_endpoint[endpoint][0].methods)
            verbs.remove("HEAD")
            verbs.remove("OPTIONS")
            url = url_for(endpoint, id=_id)
            hateos.append({"id":_id, "link":url, "methods": verbs})
            
        return hateos


# /task/{id}
class TaskSchema(HATEOASModelSchema):
    """Return the Task and the status of this task."""
    complete = fields.Boolean()
    class Meta:
        model = db.Task
    

# /task/{id}?include=result
class TaskIncludedSchema(TaskSchema):
    """Returns the TaskSchema plus the correspoding results."""
    results = fields.Nested('TaskResultSchema', many=True, exclude=['task'])

# /task/{id}/result
class TaskResultSchema(HATEOASModelSchema):
    """Return a list of results belong to the task."""
    # task = fields.Nested('TaskSchema', many=False, exclude=['results'])
    # _id = ma.URLFor('result_with_id', id='<id>')
    # task = ma.HyperlinkRelated('task_with_id')
    node = ma.HyperlinkRelated('node_with_node_id')

    class Meta:
        model = db.Result


# ------------------------------------------------------------------------------
class ResultSchema(HATEOASModelSchema):
    _id = ma.URLFor('result_with_id', id='<id>')
    task = ma.HyperlinkRelated('task_with_id')

    class Meta:
        model = db.Result

class ResultTaskIncludedSchema(ResultSchema):
    task = fields.Nested('TaskSchema', many=False)



# ------------------------------------------------------------------------------
class OrganizationSchema(HATEOASModelSchema):
    # collaborations = fields.Nested(
    #     'CollaborationSchema', 
    #     many=True, 
    #     exclude=['organizations', 'nodes', 'tasks']
    # )
    _id = ma.URLFor('organization_with_id', id='<id>')
    collaborations = ma.List(ma.HyperlinkRelated('collaboration_with_id'))
    tasks = ma.List(ma.HyperlinkRelated('task_with_id'))
    node = ma.List(ma.HyperlinkRelated('node_with_node_id'))

    class Meta:
        model = db.Organization

# ------------------------------------------------------------------------------
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