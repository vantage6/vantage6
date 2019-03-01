# -*- coding: utf-8 -*-
import types

import unittest
import doctest
import logging

from flask import Flask, Response as BaseResponse, json
from flask.testing import FlaskClient
from werkzeug.utils import cached_property

import json

from pytaskmanager import server
from pytaskmanager import util
from pytaskmanager.server import db
from pytaskmanager.server import fixtures

log = logging.getLogger(__name__.split('.')[-1])

# def load_tests(loader, tests, ignore):
#     # tests.addTests(doctest.DocTestSuite(fhir.node))
#     return tests


class Response(BaseResponse):
    @cached_property
    def json(self):
        return json.loads(self.data)


class TestNode(FlaskClient):
    def open(self, *args, **kwargs):
        if 'json' in kwargs:
            kwargs['data'] = json.dumps(kwargs.pop('json'))
            kwargs['content_type'] = 'application/json'
        return super(TestNode, self).open(*args, **kwargs)



class TestResources(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.loglevels = {}

        for lib in ['fixtures', 'db']:
            l = logging.getLogger(lib)
            cls.loglevels[lib] = l.level
            l.setLevel(logging.WARNING)

    @classmethod
    def tearDownClass(cls):
        for lib in cls.loglevels:
            l = logging.getLogger(lib)
            l.setLevel(cls.loglevels[lib])

    def setUp(self):
        """Called immediately before running a test method."""
        # Use an in-memory database
        db.init('sqlite://')
        fixtures.create()

        server.app.testing = True
        server.app.response_class = Response
        server.app.test_client_class = TestNode
        server.app.secret_key = "test-secret"

        ctx = util.TestContext()
        ctx.init(ctx.config_file)
        server.init_resources(ctx)

        self.app = server.app.test_client()

        self.credentials = {
            'username': 'root',
            'password': 'admin'
        }

    def login(self):
        tokens = self.app.post('/api/token/user', json=self.credentials).json
        headers = {
            'Authorization': 'Bearer {}'.format(tokens['access_token'])
        }
        return headers


    def test_version(self):
        rv = self.app.get('/api/version')
        r = json.loads(rv.data)
        self.assertIn('version', r) 


    def test_token(self):
        tokens = self.app.post('/api/token/user', json=self.credentials).json
        self.assertIn('access_token', tokens)
        self.assertIn('refresh_token', tokens)


    def test_organization(self):
        headers = self.login()

        # First retrieve a list of all organizations
        orgs = self.app.get('/api/organization', headers=headers).json
        self.assertEqual(len(orgs), 3)

        attrs = [
            'id',
            'name',
            'domain',
            'name',
            'address1',
            'address2',
            'zipcode',
            'country',
        ]

        org = orgs[0]
        for attr in attrs:
            self.assertIn(attr, org)

        # Retrieve a single organization
        url = '/api/organization/{}'.format(org['id'])
        org = self.app.get(url, headers=headers).json
        self.assertEqual(org['id'], orgs[0]['id'])
        self.assertEqual(org['name'], orgs[0]['name'])

        # Create a new organization
        org_details = {
            'name': 'Umbrella Corporation',
            'address1': 'Resident Evil Pike',
        }

        org = self.app.post('/api/organization', json=org_details, headers=headers).json

        for attr in attrs:
            self.assertIn(attr, org)

        self.assertGreater(org['id'], 0)

        orgs = self.app.get('/api/organization', headers=headers).json
        self.assertEqual(len(orgs), 4)


    def test_collaboration(self):
        headers = self.login()

        collaborations = self.app.get('/api/collaboration', headers=headers).json
        self.assertEqual(len(collaborations), 3)
        

