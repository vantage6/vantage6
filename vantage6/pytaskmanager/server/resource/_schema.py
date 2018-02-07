# -*- coding: utf-8 -*-

from marshmallow import fields
from marshmallow_sqlalchemy import ModelSchema, field_for

from .. import ma
from .. import db


# ------------------------------------------------------------------------------
class TaskSchema(ModelSchema):
    results = ma.List(ma.HyperlinkRelated('result'))
    collaboration = ma.HyperlinkRelated('collaboration')

    complete = fields.Boolean()

    class Meta:
        model = db.Task

class TaskIncludedSchema(TaskSchema):
    results = fields.Nested('TaskResultSchema', many=True, exclude=['task'])



# ------------------------------------------------------------------------------
class TaskResultSchema(ModelSchema):
    # task = fields.Nested('TaskSchema', many=False, exclude=['results'])
    task = ma.HyperlinkRelated('task')
    client = ma.HyperlinkRelated('client')

    class Meta:
        model = db.TaskResult


# ------------------------------------------------------------------------------
class ResultSchema(ModelSchema):
    # task = fields.Nested('TaskSchema', many=False, exclude=['results'])
    task = ma.HyperlinkRelated('task')

    class Meta:
        model = db.TaskResult

class ResultTaskIncludedSchema(ResultSchema):
    task = fields.Nested('TaskSchema', many=False)



# ------------------------------------------------------------------------------
class OrganizationSchema(ModelSchema):
    # collaborations = fields.Nested(
    #     'CollaborationSchema', 
    #     many=True, 
    #     exclude=['organizations', 'clients', 'tasks']
    # )

    collaborations = ma.List(ma.HyperlinkRelated('collaboration'))
    tasks = ma.List(ma.HyperlinkRelated('task'))
    clients = ma.List(ma.HyperlinkRelated('client'))

    class Meta:
        model = db.Organization

# ------------------------------------------------------------------------------
class CollaborationSchema(ModelSchema):
    # organizations = fields.Nested(
    #     'OrganizationSchema', 
    #     many=True, 
    #     exclude=['collaborations', 'users', 'clients', 'tasks']
    # )
    # _links = ma.Hyperlinks({
    #     'self': ma.URLFor('collaboration', id='<id>'),
    # })

    organizations = ma.List(ma.HyperlinkRelated('organization'))
    tasks = ma.List(ma.HyperlinkRelated('task'))
    clients = ma.List(ma.HyperlinkRelated('client'))

    class Meta:
        model = db.Collaboration


# ------------------------------------------------------------------------------
class ClientSchema(ModelSchema):
    organization = ma.HyperlinkRelated('organization')
    collaboration = ma.HyperlinkRelated('collaboration')

    class Meta:
        model = db.Client


# ------------------------------------------------------------------------------
class UserSchema(ModelSchema):
    
    class Meta:
        model = db.User