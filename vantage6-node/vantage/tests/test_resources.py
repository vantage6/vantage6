# -*- coding: utf-8 -*-
import types
import yaml
import unittest
import doctest
import logging
import json

from flask import Flask, Response as BaseResponse, json
from flask.testing import FlaskClient
from werkzeug.utils import cached_property

from vantage import server
from vantage import util
from vantage.server import db
from vantage.constants import APPNAME, PACAKAGE_FOLDER, VERSION
from vantage.server.controller.fixture import load
from vantage.server.model.base import Database

log = logging.getLogger(__name__.split('.')[-1])


class Response(BaseResponse):
    @cached_property
    def json(self):
        return json.loads(self.data)


class TestNode(FlaskClient):
    def open(self, *args, **kwargs):
        if 'json' in kwargs:
            kwargs['data'] = json.dumps(kwargs.pop('json'))
            kwargs['content_type'] = 'application/json'
        return super().open(*args, **kwargs)

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
        Database().connect("sqlite://")
        file_ = str(PACAKAGE_FOLDER / APPNAME / "_data" / "example_fixtures.yaml")
        with open(file_) as f:
            self.entities = yaml.safe_load(f.read())
        load(self.entities, drop_all=True)
        
        server.app.testing = True
        server.app.response_class = Response
        server.app.test_client_class = TestNode
        server.app.secret_key = "test-secret"

        
        ctx = util.TestContext.from_external_config_file(
            "unittest_config.yaml")

        server.init_resources(ctx)

        self.app = server.app.test_client()

        self.credentials = {
            'root':{
                'username': 'root',
                'password': 'password'
            },
            'admin':{
                'username': 'frank@iknl.nl',
                'password': 'password'
            },
            'user':{
                'username': 'melle@iknl.nl',
                'password': 'password'
            }
        }

    def login(self, type_='root'):
        tokens = self.app.post(
            '/api/token/user', 
            json=self.credentials[type_]
        ).json
        headers = {
            'Authorization': 'Bearer {}'.format(tokens['access_token'])
        }
        return headers

    def test_version(self):
        rv = self.app.get('/api/version')
        r = json.loads(rv.data)
        self.assertIn('version', r)
        self.assertEqual(r['version'], VERSION) 

    def test_token_different_users(self):
        for type_ in ["root", "admin", "user"]:
            tokens = self.app.post('/api/token/user', 
                json=self.credentials[type_]).json
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
            'address1': 'Resident Evil Pike'
        }

        org = self.app.post(
            '/api/organization',
            json=org_details, 
            headers=headers
        ).json

        # for attr in attrs:
        #     self.assertIn(attr, org)

        # self.assertGreater(org['id'], 0)

        orgs = self.app.get('/api/organization', headers=headers).json
        # self.assertEqual(len(orgs), 4)

    def test_collaboration(self):
        headers = self.login()

        collaborations = self.app.get(
            '/api/collaboration', headers=headers
        ).json
        self.assertEqual(len(collaborations), 3)
        
    def test_node_without_id(self):
        
        # GET
        headers = self.login("root")
        nodes = self.app.get("/api/node", headers=headers).json
        expected_fields = [
            'name', 
            'api_key', 
            'collaboration',
            'organization',
            'status',
            'id',
            'type',
            'last_seen',
            'ip'
        ]
        for node in nodes:
            for key in expected_fields: 
                self.assertIn(key, node)

        headers = self.login("user")
        nodes = self.app.get("/api/node", headers=headers).json
        self.assertIsNotNone(nodes)

        # POST
        # unknown collaboration id should fail
        response = self.app.post("/api/node", headers=headers, json={
            "collaboration_id": 99999
        })
        response_json = response.json
        self.assertIn("msg", response_json)
        self.assertEqual(response.status_code, 404) # NOT FOUND
        
        # succesfully create a node
        response = self.app.post("/api/node", headers=headers, json={
            "collaboration_id": 1
        })
        response_json = response.json
        self.assertEqual(response.status_code, 201) # CREATED
        
    def test_node_with_id(self):
        
        # root user can access all nodes
        headers = self.login("root")
        node = self.app.get("/api/node/8", headers=headers).json
        expected_fields = [
            'name', 
            'api_key', 
            'collaboration',
            'organization',
            'status',
            'id',
            'type',
            'last_seen',
            'ip'
        ]
        for key in expected_fields: 
            self.assertIn(key, node)

        # user cannot access all 
        headers = self.login("user")
        node = self.app.get("/api/node/8", headers=headers)
        self.assertEqual(node.status_code, 403)

        # some nodes just don't exist
        node = self.app.get("/api/node/9999", headers=headers)
        self.assertEqual(node.status_code, 404)

    def test_node_tasks(self):
        headers = self.login("root")
        
        # Non existing node
        task = self.app.get("/api/node/9999/task", headers=headers)
        self.assertEqual(task.status_code, 404)

        task = self.app.get("/api/node/7/task", headers=headers)
        self.assertEqual(task.status_code, 200)

        task = self.app.get("/api/node/7/task?state=open", headers=headers)
        self.assertEqual(task.status_code, 200)

    def test_result_with_id(self):
        headers = self.login("root")
        result = self.app.get("/api/result/1", headers=headers)
        self.assertEqual(result.status_code, 200)

        result = self.app.get("/api/result/1?include=task", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_result_without_id(self):
        headers = self.login("root")
        result = self.app.get("/api/result", headers=headers)
        self.assertEqual(result.status_code, 200)

        result = self.app.get("/api/result?state=open&&node_id=1", 
            headers=headers)
        self.assertEqual(result.status_code, 200)

        result = self.app.get("/api/result?task_id=1", headers=headers)
        self.assertEqual(result.status_code, 200)

        result = self.app.get("/api/result?task_id=1&&node_id=1", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_stats(self):
        headers = self.login("root")
        result = self.app.get("/api/result", headers=headers)
        self.assertEqual(result.status_code, 200)
    
    def test_task_with_id(self):
        headers = self.login("root")
        result = self.app.get("/api/task/1", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_task_witout_id(self):
        headers = self.login("root")
        result = self.app.get("/api/task", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_task_including_results(self):
        headers = self.login("root")
        result = self.app.get("/api/task?include=results", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_task_unknown(self):
        headers = self.login("root")
        result = self.app.get("/api/task/9999", headers=headers)
        self.assertEqual(result.status_code, 404)

    def test_user_with_id(self):
        headers = self.login("admin")
        result = self.app.get("/api/user/1", headers=headers)
        self.assertEqual(result.status_code, 200)
        user = result.json

        expected_fields = [
            "username",
            "firstname",
            "lastname",
            "roles"
        ]
        for field in expected_fields:
            self.assertIn(field, user)
    
    def test_user_unknown(self):
        headers = self.login("admin")
        result = self.app.get("/api/user/9999", headers=headers)
        self.assertEqual(result.status_code, 404)

    def test_user_without_id(self):
        for role in ["user", "admin", "root"]:
            headers = self.login(role)
            result = self.app.get("/api/user", headers=headers)
            self.assertEqual(result.status_code, 200)

    def test_user_post(self):
        headers = self.login("root")
        new_user = {
            "username": "unittest",
            "firstname": "unit",
            "lastname": "test",
            "roles": ["admin", "root"],
            "password": "super-secret"
        }
        result = self.app.post("/api/user", headers=headers,
            json=new_user)
        self.assertEqual(result.status_code, 201)

        result = self.app.post("/api/user", headers=headers,
            json=new_user)
        self.assertEqual(result.status_code, 400)

    def test_user_delete(self):
        headers = self.login("root")
        result = self.app.delete("/api/user/1", headers=headers)
        self.assertEqual(result.status_code, 200)
        
    def test_user_delete_unknown(self):    
        headers = self.login("root")
        result = self.app.delete("/api/user/99999", headers=headers)
        self.assertEqual(result.status_code, 404)

    def test_user_delete_forbidden(self):
        headers = self.login("user")
        result = self.app.delete("/api/user/4", headers=headers)
        self.assertEqual(result.status_code, 403)

    def test_user_patch(self):
        headers = self.login("root")
        result = self.app.patch("/api/user/1", headers=headers, json={
            "username": "root2",
            "firstname": "henk",
            "lastname": "biertje",
            "password": "wachtwoord",
            "roles": ["root"]
        })
        self.assertEqual(result.status_code, 200)

    def test_user_patch_unknown(self):
        headers = self.login("root")
        result = self.app.patch("/api/user/9999", headers=headers, json={
            "username": "root2"
        })
        self.assertEqual(result.status_code, 404)
    
    def test_user_patch_forbidden(self):
        headers = self.login("user")
        result = self.app.patch("/api/user/4", headers=headers, json={
            "username": "root2"
        })
        self.assertEqual(result.status_code, 403)
