# -*- coding: utf-8 -*-
from http import HTTPStatus
from sqlalchemy.sql.schema import PassiveDefault
import yaml
import unittest
import logging
import json
import uuid

from unittest.mock import MagicMock, patch
from flask import Response as BaseResponse
from flask.testing import FlaskClient
from werkzeug.utils import cached_property

from vantage6.common.globals import APPNAME
from vantage6.server.globals import PACAKAGE_FOLDER
from vantage6.server import ServerApp
from vantage6.server.model import Rule, Role, Organization, User
from vantage6.server.model.rule import Scope, Operation
from vantage6.server import context
from vantage6.server._version import __version__
from vantage6.server.model.base import Database
from vantage6.server.controller.fixture import load


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
        """Called immediately before running a test method."""
        Database().connect("sqlite://", allow_drop_all=True)

        ctx = context.TestContext.from_external_config_file(
            "unittest_config.yaml")

        server = ServerApp(ctx)

        file_ = str(PACAKAGE_FOLDER / APPNAME / "server" / "_data" /
                    "unittest_fixtures.yaml")
        with open(file_) as f:
            cls.entities = yaml.safe_load(f.read())
        load(cls.entities)

        cls.app = server.app.test_client()

        cls.credentials = {
            'root': {
                'username': 'root',
                'password': 'root'
            },
            'admin': {
                'username': 'frank@iknl.nl',
                'password': 'password'
            },
            'user': {
                'username': 'melle@iknl.nl',
                'password': 'password'
            },
            'user-to-delete': {
                'username': 'dont-use-me',
                'password': 'password'
            }
        }

        log.debug(User.get())
        log.debug(Role.get(1).rules)
        log.debug(Rule.get())

    @classmethod
    def tearDownClass(cls):
        Database().close()

    def login(self, type_='root'):
        tokens = self.app.post(
            '/api/token/user',
            json=self.credentials[type_]
        ).json
        headers = {
            'Authorization': 'Bearer {}'.format(tokens['access_token'])
        }
        return headers

    def create_user(self, organization=None, rules=[]):

        if not organization:
            organization = Organization(name="some-organization")

        # user details
        username = str(uuid.uuid1())
        password = "password"

        # create a temporary organization

        user = User(username=username, password=password,
                    organization=organization, email=f"{username}@test.org",
                    rules=rules)
        user.save()

        self.credentials[username] = {
            "username": username,
            "password": password
        }

        return user.username

    def create_user_and_login(self, organization=None, rules=[]):
        username = self.create_user(organization, rules)
        return self.login(username)

    def test_version(self):
        rv = self.app.get('/api/version')
        r = json.loads(rv.data)
        self.assertIn('version', r)
        self.assertEqual(r['version'], __version__)

    def test_token_different_users(self):
        for type_ in ["root", "admin", "user"]:
            tokens = self.app.post(
                '/api/token/user',
                json=self.credentials[type_]
            ).json
            self.assertIn('access_token', tokens)
            self.assertIn('refresh_token', tokens)

    def test_organization(self):
        headers = self.login()

        # First retrieve a list of all organizations
        orgs = self.app.get('/api/organization', headers=headers).json

        self.assertEqual(len(orgs), len(Organization.get()))

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
        self.assertEqual(response.status_code, 404)  # NOT FOUND

        # succesfully create a node
        response = self.app.post("/api/node", headers=headers, json={
            "collaboration_id": 1
        })
        response_json = response.json
        self.assertEqual(response.status_code, 201)  # CREATED

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

        result = self.app.get("/api/result?task_id=1&&node_id=1",
                              headers=headers)
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
            "password": "super-secret",
            "email": "unit@test.org",
        }
        result = self.app.post("/api/user", headers=headers,
                               json=new_user)
        self.assertEqual(result.status_code, 201)

        result = self.app.post("/api/user", headers=headers,
                               json=new_user)
        self.assertEqual(result.status_code, 400)

    def test_user_delete(self):
        headers = self.login("root")
        result = self.app.delete("/api/user/5", headers=headers)
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
        # print(self.app.get("/api/user/2", headers=headers).json)
        result = self.app.patch("/api/user/2", headers=headers, json={
            "firstname": "Henk",
            "lastname": "Martin"
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

    def test_root_username_forbidden(self):
        headers = self.login("root")
        results = self.app.post("/api/user", headers=headers, json={
            "username": "root",
            "firstname": "madman",
            "lastname": "idiot",
            "password": "something-really-secure"
        })
        self.assertEqual(results.status_code, 400)

    def test_root_role_forbidden(self):
        headers = self.login("root")
        new_user = {
            "username": "some",
            "firstname": "guy",
            "lastname": "there",
            "roles":  "root",
            "password": "super-secret"
        }
        result = self.app.post("/api/user", headers=headers,
                               json=new_user)
        self.assertEqual(result.status_code, 400)

    @patch("vantage6.server.mail_service.MailService.send_email")
    def test_reset_password(self, send_email):
        user_ = {
            "username": "root"
        }
        result = self.app.post("/api/recover/lost", json=user_)
        self.assertEqual(result.status_code, 200)

    @patch("vantage6.server.mail_service.MailService.send_email")
    def test_reset_password_missing_error(self, send_email):
        result = self.app.post("/api/recover/lost", json={})
        self.assertEqual(result.status_code, 400)

    @patch("vantage6.server.resource.recover.decode_token")
    def test_recover_password(self, decode_token):
        decode_token.return_value = {'identity': {'id': 1}}
        new_password = {
            "password": "$ecret88!",
            "reset_token": "token"
        }
        result = self.app.post("/api/recover/reset", json=new_password)

        self.assertEqual(result.status_code, 200)

        # verify that the new password works
        result = self.app.post("/api/token/user", json={
            "username": "root",
            "password": "$ecret88!"
        })
        self.assertIn("access_token", result.json)
        self.credentials["root"]["password"] = "$ecret88!"

    def test_fail_recover_password(self):
        result = self.app.post("/api/recover/reset", json={})
        self.assertEqual(result.status_code, 400)

    def test_view_rules(self):
        headers = self.login("root")
        result = self.app.get("/api/rule", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_view_roles(self):
        headers = self.login("root")
        result = self.app.get("/api/role", headers=headers)
        self.assertEqual(result.status_code, 200)

        body = result.json
        expected_fields = ['organization', 'name', 'description', 'users']
        for field in expected_fields:
            self.assertIn(field, body[0])

    def test_create_role_as_root(self):
        headers = self.login("root")

        # obtain available rules
        rules = self.app.get("/api/rule", headers=headers).json
        rule_ids = [rule.get("id") for rule in rules]

        # assign first two rules to role
        body = {
            "name": "some-role-name",
            "description": "Testing if we can create a role",
            "rules": rule_ids[:2]
        }

        # create role
        result = self.app.post("/api/role", headers=headers, json=body)

        # check that server responded ok
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # verify the values
        self.assertEqual(result.json.get("name"), body["name"])
        self.assertEqual(result.json.get("description"), body["description"])
        self.assertEqual(len(result.json.get("rules")), 2)

    def test_create_role_as_root_for_different_organization(self):
        headers = self.login("root")

        # obtain available rules
        rules = self.app.get("/api/rule", headers=headers).json

        # create new organization, so we're sure that the current user
        # is not assigned to the same organization
        org = Organization(name="Some-random-organization")
        org.save()

        body = {
            "name": "some-role-name",
            "description": "Testing if we can create a rol for another org",
            "rules": [rule.get("id") for rule in rules],
            "organization_id": org.id
        }

        # create role
        result = self.app.post("/api/role", headers=headers, json=body)

        # check that server responded ok
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # verify the organization
        self.assertEqual(org.id, result.json["organization"]["id"])

    def test_create_role_permissions(self):
        all_rules = Rule.get()

        # check user without any permissions
        headers = self.create_user_and_login()

        body = {
            "name": "some-role-name",
            "description": "Testing if we can create a rol for another org",
            "rules": [rule.id for rule in all_rules],
        }
        result = self.app.post("/api/role", headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # check that user with a missing rule cannot create a role with that
        # missing rule
        headers = self.create_user_and_login(rules=(all_rules[:-2]))
        result = self.app.post("/api/role", headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # check that user can create role within his organization
        rule = Rule.get_by_("manage_roles", scope=Scope.ORGANIZATION,
                            operation=Operation.CREATE)

        headers = self.create_user_and_login(rules=[rule])
        body["rules"] = [rule.id]
        result = self.app.post("/api/role", headers=headers, json=body)

        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # check a non-existing organization
        headers = self.login("root")
        body["organization_id"] = -1
        result = self.app.post('/api/role', headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # check that assigning an unexisting rule is not possible
        headers = self.create_user_and_login()
        body["rules"] = [-1]
        result = self.app.post("/api/role", headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

    def test_edit_role(self):
        headers = self.login('root')

        # create testing entities
        org = Organization(name="some-organization-name")
        org.save()
        role = Role(name="some-role-name", organization=org)
        role.save()

        # test name, description
        result = self.app.patch(f'/api/role/{role.id}', headers=headers, json={
            "name": "a-different-role-name",
            "description": "some description of this role..."
        })
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(role.name, "a-different-role-name")
        self.assertEqual(role.description, "some description of this role...")

        # test modifying rules
        all_rule_ids = [rule.id for rule in Rule.get()]
        result = self.app.patch(f'/api/role/{role.id}', headers=headers, json={
            "rules": all_rule_ids
        })
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertListEqual(all_rule_ids, [rule.id for rule in role.rules])

        # test non owning rules
        rule = Rule.get_by_("manage_roles", Scope.ORGANIZATION,
                            Operation.EDIT)
        headers = self.create_user_and_login(org, [rule])
        result = self.app.patch(f"/api/role/{role.id}", headers=headers, json={
            "rules": all_rule_ids
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test modifying role of another organization, without global
        # permission
        org2 = Organization(name="another-organization")
        headers = self.create_user_and_login(org2, [rule])
        result = self.app.patch(f'/api/role/{role.id}', headers=headers, json={
            "name": "this-will-not-be-updated"
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test modifying role with global permissions
        rule = Rule.get_by_("manage_roles", Scope.GLOBAL, Operation.EDIT)
        headers = self.create_user_and_login(org2, [rule])
        result = self.app.patch(f'/api/role/{role.id}', headers=headers, json={
            "name": "this-will-not-be-updated"
        })
        self.assertEqual(result.status_code, HTTPStatus.OK)

    def test_remove_role(self):

        org = Organization()
        org.save()
        role = Role(organization=org)
        role.save()

        # test removal without permissions
        headers = self.create_user_and_login()
        result = self.app.delete(f'/api/role/{role.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test removal with organization permissions
        rule = Rule.get_by_("manage_roles", Scope.ORGANIZATION,
                            Operation.DELETE)
        headers = self.create_user_and_login(org, [rule])
        result = self.app.delete(f'/api/role/{role.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test failed removal with organization permissions
        role = Role(organization=org)  # because we removed it...
        role.save()
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.delete(f'/api/role/{role.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test removal with global permissions
        rule = Rule.get_by_("manage_roles", Scope.GLOBAL, Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.delete(f'/api/role/{role.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
