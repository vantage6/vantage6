# -*- coding: utf-8 -*-

from marshmallow import fields
from marshmallow_sqlalchemy import ModelSchema, field_for

from .. import ma
from .. import db


# ------------------------------------------------------------------------------
class TaskSchema(ModelSchema):
    _id = ma.URLFor('task_with_id', id='<id>')
    results = ma.List(ma.HyperlinkRelated('result_with_id'))
    collaboration = ma.HyperlinkRelated('collaboration_without_id')

    complete = fields.Boolean()

    class Meta:
        model = db.Task

class TaskIncludedSchema(TaskSchema):
    results = fields.Nested('TaskResultSchema', many=True, exclude=['task'])



# ------------------------------------------------------------------------------
class TaskResultSchema(ModelSchema):
    # task = fields.Nested('TaskSchema', many=False, exclude=['results'])
    _id = ma.URLFor('result_with_id', id='<id>')
    # task = ma.HyperlinkRelated('task_with_id')
    # node = ma.HyperlinkRelated('node_with_node_id')

    class Meta:
        model = db.Result


# ------------------------------------------------------------------------------
class ResultSchema(ModelSchema):
    # task = fields.Nested('TaskSchema', many=False, exclude=['results'])
    _id = ma.URLFor('result_with_id', id='<id>')
    task = ma.HyperlinkRelated('task_with_id')

    class Meta:
        model = db.Result

class ResultTaskIncludedSchema(ResultSchema):
    task = fields.Nested('TaskSchema', many=False)



# ------------------------------------------------------------------------------
class OrganizationSchema(ModelSchema):
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
class CollaborationSchema(ModelSchema):
    # organizations = fields.Nested(
    #     'OrganizationSchema', 
    #     many=True, 
    #     exclude=['collaborations', 'users', 'nodes', 'tasks']
    # )
    # _links = ma.Hyperlinks({
    #     'self': ma.URLFor('collaboration', id='<id>'),
    # })

    organizations = ma.List(ma.HyperlinkRelated('organization_with_id'))
    tasks = ma.List(ma.HyperlinkRelated('task_with_id'))
    nodes = ma.List(ma.HyperlinkRelated('node_with_node_id'))

    class Meta:
        model = db.Collaboration


# ------------------------------------------------------------------------------
class CollaborationSchemaSimple(ModelSchema):

    nodes = fields.Nested(
        'NodeSchemaSimple', 
        many=True, 
        exclude=['nodes', 'tasks', 'collaboration']
    )

    class Meta:
        model = db.Collaboration
        exclude = [
            'tasks',
            'organizations',
            # 'nodes',
        ]


# ------------------------------------------------------------------------------
class NodeSchema(ModelSchema):
    # organization = ma.HyperlinkRelated('organization_with_id')
    # collaboration = ma.HyperlinkRelated('collaboration_with_id')

    class Meta:
        model = db.Node


# ------------------------------------------------------------------------------
class NodeSchemaSimple(ModelSchema):

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
class UserSchema(ModelSchema):
    
    class Meta:
        model = db.User