#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database Model."""
from __future__ import print_function, unicode_literals
import uuid

from pytaskmanager.server import db
from pytaskmanager import util

import logging

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def createOrganizations():
    log.info('Creating organizations')

    organizations = [
    {
        "name": "Small Organization",
        "domain": "small-organization.example",
        "address1": "Big Ambitions Drive 4",
        "address2": "",
        "zipcode": "12345",
        "country": "Nowhereland"
    },
    {
        "name": "Big Organization",
        "domain": "big-organization.example",
        "address1": "Offshore Accounting Drive 19",
        "address2": "",
        "zipcode": "54331",
        "country": "Nowhereland"
    },
    {
        "name": "SouthParkCancerRegister",
        "domain": "southpark.example",
        "address1": "Street 1",
        "address2": "",
        "zipcode": "66666",
        "country": "United States"
    }
    ]

    for org_dict in organizations:
        o = db.Organization(**org_dict)
        o.save()


def createCollaborations():
    log.info('Creating collaborations')

    collaborations = [
    {
        "name": "The Big Small Consortium",
        "description": "",
        "participants": [
            "Small Organization", 
            "Big Organization", 
            "SouthParkCancerRegister"
        ]
    },
    {
        "name": "The Small Big Consortium",
        "description": "",
        "participants": [
            "Big Organization", 
            "SouthParkCancerRegister"
        ]
    },
    {
        "name": "The Useless Consortium",
        "description": "Consortium with a single organization",
        "participants": [
            "SouthParkCancerRegister",
        ]
    },
    ]

    for collab_dict in collaborations:
        collaboration = db.Collaboration()
        collaboration.name = collab_dict['name']
        collaboration.description = collab_dict['description']

        session = db.Session()
        for org_name in collab_dict['participants']:
            query = session.query(db.Organization)
            query = query.filter_by(name=org_name)
            org = query.one()

            collaboration.organizations.append(org)

        collaboration.save()


def createClients():
    log.info('Creating clients')

    for organization in db.Organization.get():
        for collaboration in organization.collaborations:
            client = db.Client()
            client.name = "{} - {} Client".format(organization.name, collaboration.name)
            client.api_key = str(uuid.uuid1())
            client.organization = organization
            client.collaboration = collaboration
            log.debug(' - API-key for "{}": {}'.format(client.name, client.api_key))

        organization.save()


def createUsers():
    log.info('Creating users')

    for organization in db.Organization.get():
        user = db.User()
        user.organization = organization
        user.username = 'admin@{}'.format(organization.domain)
        user.firstname = 'Administrator'
        user.set_password('password')
        user.roles = 'admin'

    organization.save()

    root = db.User()
    root.username = 'root'
    root.firstname = 'root'
    root.lastname = ''
    root.set_password('admin')
    root.roles = 'root'
    root.save()


def createTasks():
    log.info('Creating tasks')

    counter = 1

    for collaboration in db.Collaboration.get():
        task = db.Task()
        task.name = 'Task {}'.format(counter)
        task.description = 'Task for {}'.format(collaboration.name)
        task.image = 'hello-world'        
        task.status = 'open'
        task.collaboration = collaboration

        for client in collaboration.clients:
            result = db.TaskResult()
            result.client = client
            result.task = task

        task.save()
        counter += 1

# ------------------------------------------------------------------------------
# create_fixtures
# ------------------------------------------------------------------------------
def create():
    createOrganizations()
    createUsers()
    createCollaborations()
    createClients()
    createTasks()


def init(ctx):
    uri = ctx.get_database_location()
    db.init(uri, drop_all=True)


