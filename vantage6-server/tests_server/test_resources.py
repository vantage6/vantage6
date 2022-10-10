# -*- coding: utf-8 -*-
import datetime
from uuid import uuid1
import yaml
import unittest
import logging
import json
import uuid

from http import HTTPStatus
from unittest.mock import patch
from flask import Response as BaseResponse
from flask.testing import FlaskClient
from werkzeug.utils import cached_property

from vantage6.common import logger_name
from vantage6.common.globals import APPNAME
from vantage6.server.globals import PACAKAGE_FOLDER
from vantage6.server import ServerApp, db
from vantage6.server.model import (Rule, Role, Organization, User, Node,
                                   Collaboration, Task, Result)
from vantage6.server.model.rule import Scope, Operation
from vantage6.server import context
from vantage6.server._version import __version__
from vantage6.server.model.base import Database, DatabaseSessionManager
from vantage6.server.controller.fixture import load


logger = logger_name(__name__)
log = logging.getLogger(logger)


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
        cls.server = server

        file_ = str(PACAKAGE_FOLDER / APPNAME / "server" / "_data" /
                    "unittest_fixtures.yaml")
        with open(file_) as f:
            cls.entities = yaml.safe_load(f.read())
        load(cls.entities)

        server.app.testing = True
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

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()

    @classmethod
    def setUp(cls):
        # set db.session
        DatabaseSessionManager.get_session()

    @classmethod
    def tearDown(cls):
        # unset db.session
        DatabaseSessionManager.clear_session()

    def login(self, type_='root'):
        with self.server.app.test_client() as client:
            tokens = client.post(
                '/api/token/user',
                json=self.credentials[type_]
            ).json
        if 'access_token' in tokens:
            headers = {
                'Authorization': 'Bearer {}'.format(tokens['access_token'])
            }
            return headers
        else:
            print('something wrong, during login:')
            print(tokens)
            return None

    def create_user(self, organization=None, rules=[], password="password"):

        if not organization:
            organization = Organization(name="some-organization")
            organization.save()

        # user details
        username = str(uuid.uuid1())

        # create a temporary organization
        user = User(username=username, password=password,
                    organization=organization, email=f"{username}@test.org",
                    rules=rules)
        user.save()

        self.credentials[username] = {
            "username": username,
            "password": password
        }

        return user

    def create_node(self, organization=None, collaboration=None):
        if not organization:
            organization = Organization()

        if not collaboration:
            collaboration = Collaboration()

        api_key = str(uuid1())
        node = Node(
            name=str(uuid1()),
            api_key=api_key,
            organization=organization,
            collaboration=collaboration
        )
        node.save()

        return node, api_key

    def login_node(self, api_key):
        tokens = self.app.post(
            '/api/token/node',
            json={"api_key": api_key}
        ).json
        if 'access_token' in tokens:
            headers = {
                'Authorization': 'Bearer {}'.format(tokens['access_token'])
            }
        else:
            print(tokens)

        return headers

    def login_container(self, collaboration=None, organization=None,
                        node=None, task=None, api_key=None):
        if not node:
            if not collaboration:
                collaboration = Collaboration()
            if not organization:
                organization = Organization()
            api_key = str(uuid1())
            node = Node(organization=organization, collaboration=collaboration,
                        api_key=api_key)
            node.save()
        else:
            collaboration = node.collaboration
            organization = node.organization

        if not task:
            task = Task(image="some-image", collaboration=collaboration,
                        results=[Result()])
            task.save()

        headers = self.login_node(api_key)
        tokens = self.app.post('/api/token/container', headers=headers, json={
            "image": "some-image",
            "task_id": task.id
        }
        ).json

        if 'msg' in tokens:
            print(tokens['msg'])

        headers = {
            'Authorization': 'Bearer {}'.format(tokens['container_token'])
        }
        return headers

    def create_node_and_login(self, *args, **kwargs):
        node, api_key = self.create_node(*args, **kwargs)
        return self.login_node(api_key)

    def create_user_and_login(self, organization=None, rules=[]):
        user = self.create_user(organization, rules)
        return self.login(user.username)

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

        rule = Rule.get_by_("organization", Scope.GLOBAL,
                            Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])

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
        url = f'/api/organization/{org["id"]}'
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
        org = Organization()
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(organization=org, rules=[rule])

        collaborations = self.app.get(
            '/api/collaboration', headers=headers
        )
        self.assertEqual(collaborations.status_code, HTTPStatus.OK)
        db_cols = Collaboration.get()
        self.assertEqual(len(collaborations.json), len(db_cols))

    def test_node_without_id(self):

        # GET
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        nodes = self.app.get("/api/node", headers=headers).json
        expected_fields = [
            'name',
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

        nodes = self.app.get("/api/node", headers=headers).json
        self.assertIsNotNone(nodes)

        # POST
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.CREATE)
        headers = self.create_user_and_login(rules=[rule])
        # unknown collaboration id should fail
        response = self.app.post("/api/node", headers=headers, json={
            "collaboration_id": 99999
        })
        response_json = response.json
        self.assertIn("msg", response_json)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # succesfully create a node
        org = Organization()
        col = Collaboration(organizations=[org])
        col.save()

        headers = self.create_user_and_login(org, rules=[rule])
        response = self.app.post("/api/node", headers=headers, json={
            "collaboration_id": col.id
        })
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    def test_node_with_id(self):

        # root user can access all nodes
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        node = self.app.get("/api/node/8", headers=headers).json
        expected_fields = [
            'name',
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
        headers = self.create_user_and_login()
        node = self.app.get("/api/node/8", headers=headers)
        self.assertEqual(node.status_code, HTTPStatus.UNAUTHORIZED)

        # some nodes just don't exist
        node = self.app.get("/api/node/9999", headers=headers)
        self.assertEqual(node.status_code, 404)

    def test_result_with_id(self):
        headers = self.login("root")
        result = self.app.get("/api/result/1", headers=headers)
        self.assertEqual(result.status_code, 200)

        result = self.app.get("/api/result/1?include=task", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_result_without_id(self):
        headers = self.login("root")
        result1 = self.app.get("/api/result", headers=headers)
        self.assertEqual(result1.status_code, 200)

        result2 = self.app.get("/api/result?state=open&&node_id=1",
                               headers=headers)
        self.assertEqual(result2.status_code, 200)

        result3 = self.app.get("/api/result?task_id=1", headers=headers)
        self.assertEqual(result3.status_code, 200)

        result4 = self.app.get("/api/result?task_id=1&&node_id=1",
                               headers=headers)
        self.assertEqual(result4.status_code, 200)

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
            "email": "unit@test.org",
        }
        # with a bad password, user should not be created
        new_user['password'] = "1234"
        result = self.app.post('/api/user', headers=headers, json=new_user)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

        new_user['password'] = "Welkom01!"
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

    def test_user_patch(self):
        headers = self.login("root")
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
        decode_token.return_value = {'sub': {'id': 1}}
        new_password = {
            "password": "$Ecret88!",
            "reset_token": "token"
        }
        result = self.app.post("/api/recover/reset", json=new_password)
        self.assertEqual(result.status_code, 200)

        # verify that the new password works
        result = self.app.post("/api/token/user", json={
            "username": "root",
            "password": "$Ecret88!"
        })
        self.assertIn("access_token", result.json)
        self.credentials["root"]["password"] = "$Ecret88!"

    def test_fail_recover_password(self):
        result = self.app.post("/api/recover/reset", json={})
        self.assertEqual(result.status_code, 400)

    def test_change_password(self):
        user = self.create_user(password="Password1!")
        headers = self.login(user.username)

        # test if fails when not providing correct data
        result = self.app.patch("/api/password/change", headers=headers, json={
            "current_password": "Password1!"
        })
        self.assertEqual(result.status_code, 400)
        result = self.app.patch("/api/password/change", headers=headers, json={
            "new_password": "a_new_password"
        })
        self.assertEqual(result.status_code, 400)

        # test if fails when wrong password is provided
        result = self.app.patch("/api/password/change", headers=headers, json={
            "current_password": "wrong_password1!",
            "new_password": "a_new_password"
        })
        self.assertEqual(result.status_code, 401)

        # test if fails when new password is the same
        result = self.app.patch("/api/password/change", headers=headers, json={
            "current_password": "Password1!",
            "new_password": "Password1!"
        })
        self.assertEqual(result.status_code, 400)

        # test if it works when used as intended
        result = self.app.patch("/api/password/change", headers=headers, json={
            "current_password": "Password1!",
            "new_password": "A_new_password1"
        })
        self.assertEqual(result.status_code, 200)
        db.session.refresh(user)
        self.assertTrue(user.check_password("A_new_password1"))

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
        rule = Rule.get_by_("role", scope=Scope.ORGANIZATION,
                            operation=Operation.CREATE)

        headers = self.create_user_and_login(rules=[rule])
        body["rules"] = [rule.id]
        result = self.app.post("/api/role", headers=headers, json=body)

        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # check a non-existing organization
        headers = self.login("root")
        body["organization_id"] = 9999
        result = self.app.post('/api/role', headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # check that assigning an unexisting rule is not possible
        headers = self.create_user_and_login()
        body["rules"] = [9999]
        result = self.app.post("/api/role", headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

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

        db.session.refresh(role)
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
        rule = Rule.get_by_("role", Scope.ORGANIZATION,
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
        rule = Rule.get_by_("role", Scope.GLOBAL, Operation.EDIT)
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
        rule = Rule.get_by_("role", Scope.ORGANIZATION,
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
        rule = Rule.get_by_("role", Scope.GLOBAL, Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.delete(f'/api/role/{role.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

    def test_rules_from_role(self):
        headers = self.login('root')
        role = Role.get()[0]

        result = self.app.get(f'/api/role/{role.id}/rule', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(role.rules), len(result.json))

        result = self.app.get('/api/role/9999/rule', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

    def test_add_single_rule_to_role(self):
        headers = self.login('root')

        role = Role(name="empty", organization=Organization())
        role.save()

        # role without rules
        result = self.app.get(f'/api/role/{role.id}/rule', headers=headers)

        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(result.json), 0)

        rule = Rule.get()[0]

        # try to add rule to non existing role
        result = self.app.post(f'/api/role/9999/rule/{rule.id}',
                               headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # try to add non existent rule
        result = self.app.post(f'/api/role/{role.id}/rule/9999',
                               headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # add a rule to a role
        result = self.app.post(f'/api/role/{role.id}/rule/{rule.id}',
                               headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # check that the role now has one rule
        result = self.app.get(f'/api/role/{role.id}/rule', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(result.json), 1)

    def test_remove_single_rule_from_role(self):
        headers = self.login('root')

        rule = Rule.get()[0]
        role = Role(name="unit", organization=Organization(), rules=[rule])
        role.save()

        # try to add rule to non existing role
        result = self.app.delete(f'/api/role/9999/rule/{rule.id}',
                                 headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # try to add non existent rule
        result = self.app.delete(f'/api/role/{role.id}/rule/9999',
                                 headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        result = self.app.get(f'/api/role/{role.id}/rule', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(result.json), 1)

        result = self.app.delete(f'/api/role/{role.id}/rule/{rule.id}',
                                 headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(result.json), 0)

    def test_view_permission_rules(self):
        rule = Rule.get_by_("role", Scope.ORGANIZATION, Operation.VIEW)

        role = Role(name="some-role", organization=Organization())
        role.save()

        # user does not belong to organization
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.get(f'/api/role/{role.id}/rule', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # user does belong to the organization
        headers = self.create_user_and_login(organization=role.organization,
                                             rules=[rule])
        result = self.app.get(f'/api/role/{role.id}/rule', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # user has global permissions
        rule = Rule.get_by_("role", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.get(f'/api/role/{role.id}/rule', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        role.delete()

    def test_add_rule_to_role_permission(self):

        role = Role(name="new-role", organization=Organization())
        role.save()

        rule = Rule.get_by_("role", Scope.ORGANIZATION, Operation.EDIT)

        # try adding a rule without any permission
        headers = self.create_user_and_login()
        result = self.app.post(f'/api/role/{role.id}/rule/{rule.id}',
                               headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # you cant edit other organizations roles
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.post(f'/api/role/{role.id}/rule/{rule.id}',
                               headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # you can edit other organizations with the global permission
        rule = Rule.get_by_("role", Scope.GLOBAL, Operation.EDIT)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.post(f'/api/role/{role.id}/rule/{rule.id}',
                               headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # however you can only assign rules that you own
        rule = Rule.get_by_("role", Scope.ORGANIZATION, Operation.EDIT)
        result = self.app.post(f'/api/role/{role.id}/rule/{rule.id}',
                               headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        role.delete()

    def test_remove_rule_from_role_permissions(self):

        role = Role(name="new-role", organization=Organization())
        role.save()
        rule = Rule.get_by_("role", Scope.ORGANIZATION,
                            Operation.DELETE)

        # try removing without any permissions
        headers = self.create_user_and_login()
        result = self.app.delete(f'/api/role/{role.id}/rule/{rule.id}',
                                 headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # try removing rule from other organization
        headers = self.create_user_and_login(organization=Organization(),
                                             rules=[rule])
        result = self.app.delete(f'/api/role/{role.id}/rule/{rule.id}',
                                 headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # try removing rule which is not in the role
        headers = self.create_user_and_login(organization=role.organization,
                                             rules=[rule])
        result = self.app.delete(f'/api/role/{role.id}/rule/{rule.id}',
                                 headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        role.rules.append(rule)
        role.save()

        # lets try that again
        headers = self.create_user_and_login(organization=role.organization,
                                             rules=[rule])
        result = self.app.delete(f'/api/role/{role.id}/rule/{rule.id}',
                                 headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        role.rules.append(rule)
        role.save()

        # power users can edit other organization rules
        power_rule = Rule.get_by_("role", Scope.GLOBAL,
                                  Operation.DELETE)
        headers = self.create_user_and_login(rules=[power_rule, rule])
        result = self.app.delete(f'/api/role/{role.id}/rule/{rule.id}',
                                 headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        role.delete()

    def test_view_permission_user(self):

        # user not found
        headers = self.create_user_and_login()
        result = self.app.get('/api/user/9999', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # try to view users without any permissions
        headers = self.create_user_and_login()
        result = self.app.get('/api/user', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # root user can view all users
        headers = self.login('root')
        result = self.app.get('/api/user', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(result.json), len(User.get()))

        # view users of your organization
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.VIEW)
        org = Organization.get(1)
        headers = self.create_user_and_login(org, rules=[rule])
        result = self.app.get('/api/user', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(result.json), len(org.users))

        # view a single user of your organization
        user_id = org.users[0].id
        result = self.app.get(f'/api/user/{user_id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # user can view their own data. This should always be possible
        user = self.create_user(rules=[])
        headers = self.login(user.username)
        result = self.app.get(f'/api/user/{user.id}', headers=headers)

    def test_bounce_existing_username_and_email(self):
        headers = self.create_user_and_login()
        User(username="something", email="mail@me.org").save()
        userdata = {
            "username": "not-important",
            "firstname": "name",
            "lastname": "lastname",
            "password": "welkom01",
            "email": "mail@me.org"
        }
        result = self.app.post('/api/user', headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

        userdata['username'] = 'not-important'
        result = self.app.post('/api/user', headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

    def test_new_permission_user(self):
        userdata = {
            "username": "smarty",
            "firstname": "Smart",
            "lastname": "Pants",
            "password": "Welkom01!",
            "email": "mail-us@me.org"
        }

        # Creating users for other organizations can only be by global scope
        org = Organization()
        rule = Rule.get_by_("user", Scope.ORGANIZATION,
                            Operation.CREATE)
        userdata['organization_id'] = 1
        headers = self.create_user_and_login(org, rules=[rule])
        result = self.app.post('/api/user', headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # you can do that when you have the global scope
        gl_rule = Rule.get_by_("user", Scope.GLOBAL, Operation.CREATE)
        userdata['rules'] = [gl_rule.id]
        headers = self.create_user_and_login(org, rules=[gl_rule])
        result = self.app.post('/api/user', headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # you need to own all rules in order to assign them
        headers = self.create_user_and_login(org, rules=[rule])
        userdata['username'] = 'smarty2'
        userdata['email'] = 'mail2@me.org'
        result = self.app.post('/api/user', headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # you can only assign roles in which you have all rules
        headers = self.create_user_and_login(org, rules=[rule])
        role = Role(rules=[rule], organization=org)
        role.save()
        userdata['username'] = 'smarty3'
        userdata['email'] = 'mail3@me.org'
        userdata['roles'] = [role.id]
        del userdata['organization_id']
        del userdata['rules']
        result = self.app.post('/api/user', headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)
        self.assertEqual(len(result.json['roles']), 1)

    def test_patch_user_permissions(self):

        org = Organization()
        user = User(firstname="Firstname", lastname="Lastname",
                    username="Username", password="Password", email="a@b.c",
                    organization=org)
        user.save()
        self.credentials[user.username] = {'username': user.username,
                                           'password': "Password"}

        # check non-existing user
        headers = self.create_user_and_login()
        result = self.app.patch('/api/user/9999', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # patching without permissions
        headers = self.create_user_and_login()
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'firstname': 'this-aint-gonna-fly'
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual("Username", user.username)

        # patch as a user of other organization
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.EDIT)
        self.create_user_and_login(rules=[rule])
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'firstname': 'this-aint-gonna-fly'
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual("Username", user.username)

        # patch as another user from the same organization
        rule = Rule.get_by_("user", Scope.OWN, Operation.EDIT)
        self.create_user_and_login(user.organization, [rule])
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'firstname': 'this-aint-gonna-fly'
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual("Username", user.username)

        # edit 'simple' fields
        rule = Rule.get_by_("user", Scope.OWN, Operation.EDIT)
        user.rules.append(rule)
        user.save()
        headers = self.login(user.username)
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'firstname': 'yeah'
        })
        db.session.refresh(user)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual("yeah", user.firstname)

        # edit other user within your organization
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.EDIT)
        headers = self.create_user_and_login(organization=user.organization,
                                             rules=[rule])
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'firstname': 'whatever'
        })
        db.session.refresh(user)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual("whatever", user.firstname)

        # check that password cannot be edited
        rule = Rule.get_by_("user", Scope.GLOBAL, Operation.EDIT)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'password': 'keep-it-safe'
        })
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

        # edit user from different organization, and test other edit fields
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'firstname': 'again',
            'lastname': 'and again',
        })
        db.session.refresh(user)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual("again", user.firstname)
        self.assertEqual("and again", user.lastname)

        # test that you cannot assign rules that you not own
        not_owning_rule = Rule.get_by_("user", Scope.OWN,
                                       Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'rules': [not_owning_rule.id]
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test that you cannot assign role that has rules that you do not own
        role = Role(name="somename", rules=[not_owning_rule],
                    organization=org)
        role.save()
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'rules': [role.id]
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test that you cannot assign rules if you don't have all the rules
        # that the other user has
        headers = self.create_user_and_login(rules=[rule, not_owning_rule])
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'rules': [not_owning_rule.id, rule.id]
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test that you CAN change the rules. To do so, a user is generated
        # that has same rules as current user, but also rule to edit other
        # users and another one current user does not possess
        assigning_user_rules = user.rules
        assigning_user_rules.append(
            Rule.get_by_("user", Scope.GLOBAL, Operation.EDIT)
        )
        assigning_user_rules.append(not_owning_rule)
        headers = self.create_user_and_login(rules=assigning_user_rules)
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'rules': [not_owning_rule.id, rule.id]
        })
        self.assertEqual(result.status_code, HTTPStatus.OK)
        user_rule_ids = [rule['id'] for rule in result.json['rules']]
        self.assertIn(not_owning_rule.id, user_rule_ids)

        # test that you cannot assign roles if you don't have all the
        # permissions for that role yourself (even though you have permission
        # to assign roles)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'roles': [role.id]
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test that you CAN assign roles
        headers = self.create_user_and_login(rules=[rule, not_owning_rule])
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'roles': [role.id]
        })
        self.assertEqual(result.status_code, HTTPStatus.OK)
        user_role_ids = [role['id'] for role in result.json['roles']]
        self.assertIn(role.id, user_role_ids)

        # test that you CANNOT assign roles from different organization
        other_org_role = Role(name="somename", rules=[not_owning_rule],
                              organization=Organization())
        headers = self.create_user_and_login(rules=[rule, not_owning_rule])
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'roles': [other_org_role.id]
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test missing role
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'roles': [9999]
        })
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # test missing rule
        result = self.app.patch(f'/api/user/{user.id}', headers=headers, json={
            'rules': [9999]
        })
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        user.delete()
        role.delete()

    def test_delete_user_permissions(self):

        user = User(firstname="Firstname", lastname="Lastname",
                    username="Username", password="Password", email="a@b.c",
                    organization=Organization())
        user.save()
        self.credentials[user.username] = {'username': user.username,
                                           'password': "Password"}

        # check non-exsitsing user
        headers = self.create_user_and_login()
        result = self.app.delete('/api/user/9999', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # try to delete without any permissions
        headers = self.create_user_and_login()
        result = self.app.delete(f'/api/user/{user.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # same organization but missing permissions
        rule = Rule.get_by_("user", Scope.OWN, Operation.DELETE)
        headers = self.create_user_and_login(organization=user.organization,
                                             rules=[rule])
        result = self.app.delete(f'/api/user/{user.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # other organization with organization scope
        rule = Rule.get_by_("user", Scope.ORGANIZATION,
                            Operation.DELETE)
        headers = self.create_user_and_login(organization=Organization(),
                                             rules=[rule])
        result = self.app.delete(f'/api/user/{user.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # delete yourself
        rule = Rule.get_by_("user", Scope.OWN, Operation.DELETE)
        user.rules.append(rule)
        user.save()
        headers = self.login(user.username)
        result = self.app.delete(f'/api/user/{user.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        # User is deleted by the endpoint! user.delete()

        # delete colleague
        user = User(firstname="Firstname", lastname="Lastname",
                    username="Username", password="Password", email="a@b.c",
                    organization=Organization())
        user.save()
        rule = Rule.get_by_("user", Scope.ORGANIZATION,
                            Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule],
                                             organization=user.organization)
        result = self.app.delete(f'/api/user/{user.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        # User is deleted by the endpoint user.delete()

        # delete as root
        user = User(firstname="Firstname", lastname="Lastname",
                    username="Username", password="Password", email="a@b.c",
                    organization=Organization())
        user.save()
        rule = Rule.get_by_("user", Scope.GLOBAL, Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.delete(f'/api/user/{user.id}', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        # user is deleted by endpoint! user.delete()

    def test_view_organization_as_user_permissions(self):

        # view without any permissions
        headers = self.create_user_and_login()
        result = self.app.get('/api/organization', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # view your own organization
        rule = Rule.get_by_("organization", Scope.ORGANIZATION,
                            Operation.VIEW)
        user = self.create_user(rules=[rule])
        headers = self.login(user.username)
        result = self.app.get(f'/api/organization/{user.organization.id}',
                              headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # try to view another organization without permission
        org = Organization()
        org.save()
        result = self.app.get(f'/api/organization/{org.id}',
                              headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # Missing organization with global view
        rule = Rule.get_by_("organization", Scope.GLOBAL,
                            Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.get('/api/organization/9999',
                              headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # test global view
        result = self.app.get(f'/api/organization/{org.id}',
                              headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

    def test_view_organization_as_node_permission(self):
        node, api_key = self.create_node()
        headers = self.login_node(api_key)

        # test list organization with only your organization
        result = self.app.get('/api/organization', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(result.json[0]['id'], node.organization.id)

        # test list organization
        result = self.app.get(
            f'/api/organization/{node.organization.id}',
            headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(result.json['id'], node.organization.id)
        node.delete()

    def test_view_organization_as_container_permission(self):
        node, api_key = self.create_node()
        headers = self.login_container(node=node, api_key=api_key)

        # try to get organization where he runs
        result = self.app.get(
            f'/api/organization/{node.organization.id}',
            headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(result.json['id'], node.organization.id)

        # get all organizations in the collaboration
        result = self.app.get(
            '/api/organization',
            headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertIsInstance(result.json, list)

        # cleanup
        node.delete()

    def test_create_organization_permissions(self):

        # try creating an organization without permissions
        headers = self.create_user_and_login()
        result = self.app.post('/api/organization', headers=headers, json={
            'name': 'this-aint-gonna-happen'
        })
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # create an organization
        rule = Rule.get_by_("organization", Scope.GLOBAL,
                            Operation.CREATE)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.post('/api/organization', headers=headers, json={
            'name': 'this-is-gonna-happen'
        })
        self.assertEqual(result.status_code, HTTPStatus.CREATED)
        self.assertIsNotNone(Organization.get_by_name("this-is-gonna-happen"))

    def test_patch_organization_permissions(self):

        # unknown organization
        headers = self.create_user_and_login()
        results = self.app.patch('/api/organization/9999', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # try to change anything without permissions
        org = Organization(name="first-name")
        org.save()
        results = self.app.patch(f'/api/organization/{org.id}',
                                 headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # change as super user
        rule = Rule.get_by_("organization", Scope.GLOBAL,
                            Operation.EDIT)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.patch(f'/api/organization/{org.id}',
                                 headers=headers, json={
                                     "name": "second-name"
                                 })
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json['name'], "second-name")

        # change as organization editor
        rule = Rule.get_by_("organization", Scope.ORGANIZATION,
                            Operation.EDIT)
        headers = self.create_user_and_login(organization=org, rules=[rule])
        results = self.app.patch(f'/api/organization/{org.id}',
                                 headers=headers, json={
                                     "name": "third-name"
                                 })
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json['name'], "third-name")

        # change other organization as organization editor
        rule = Rule.get_by_("organization", Scope.ORGANIZATION,
                            Operation.EDIT)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.patch(f'/api/organization/{org.id}',
                                 headers=headers, json={
                                     "name": "third-name"
                                 })
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

    def test_organization_view_nodes(self):

        # create organization, collaboration and node
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()
        node = Node(organization=org, collaboration=col)
        node.save()

        # try to view without permissions
        headers = self.create_user_and_login(org)
        results = self.app.get(f"/api/organization/{org.id}/node",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view with organization permissions
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.create_user_and_login(org, rules=[rule])
        results = self.app.get(f"/api/organization/{org.id}/node",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view other organization
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f"/api/organization/{org.id}/node",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view with global permissions
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f"/api/organization/{org.id}/node",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view as node
        headers = self.create_node_and_login(organization=org)
        results = self.app.get(f"/api/organization/{org.id}/node",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view as node from another organization
        headers = self.create_node_and_login()
        results = self.app.get(f"/api/organization/{org.id}/node",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        node.delete()

    def test_organization_view_collaboration_permissions(self):

        # test unknown organization
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        headers = self.create_user_and_login()
        results = self.app.get('/api/organization/9999/collaboration',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test view without any permission
        results = self.app.get(f'/api/organization/{org.id}/collaboration',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test view with organization scope
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION,
                            Operation.VIEW)
        headers = self.create_user_and_login(organization=org, rules=[rule])
        results = self.app.get(f'/api/organization/{org.id}/collaboration',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test view with organization scope other organiation
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f'/api/organization/{org.id}/collaboration',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test view with global scope
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f'/api/organization/{org.id}/collaboration',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test as node
        headers = self.create_node_and_login(organization=org,
                                             collaboration=col)
        results = self.app.get(f'/api/organization/{org.id}/collaboration',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_view_collaboration_permissions(self):

        # setup organization and collaboration
        org = Organization()
        col = Collaboration(organizations=[org])
        col.save()

        # try view the collaboration without any permissions
        headers = self.create_user_and_login(organization=org)
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view it with organization permissions
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION,
                            Operation.VIEW)
        headers = self.create_user_and_login(organization=org, rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view it from an outside organization
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION,
                            Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # view it with global view permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test access as node
        headers = self.create_node_and_login(organization=org,
                                             collaboration=col)
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test access as container
        headers = self.login_container(collaboration=col, organization=org)
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        org.delete()
        col.delete()

    def test_edit_collaboration_permissions(self):

        # test an unknown collaboration
        headers = self.create_user_and_login()
        results = self.app.patch("/api/collaboration/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test editing without any permission
        col = Collaboration(name="collaboration-1")
        col.save()
        headers = self.create_user_and_login()
        results = self.app.patch(f"/api/collaboration/{col.id}",
                                 headers=headers, json={
                                     "name": "this-aint-gonna-fly"
                                 })
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test editing with global permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.patch(f"/api/collaboration/{col.id}",
                                 headers=headers, json={
                                     "name": "this-is-gonna-fly"
                                 })
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "this-is-gonna-fly")

    def test_delete_collaboration_permissions(self):

        col = Collaboration()
        col.save()

        # test deleting unknown collaboration
        headers = self.create_user_and_login()
        results = self.app.delete("/api/collaboration/9999",
                                  headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test deleting without permission
        results = self.app.delete(f"/api/collaboration/{col.id}",
                                  headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test deleting with permission
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.delete(f"/api/collaboration/{col.id}",
                                  headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_view_collaboration_organization_permissions_as_user(self):
        headers = self.create_user_and_login()

        # non-existing collaboration
        results = self.app.get("/api/collaboration/9999/organization",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        # access without the proper permissions
        headers = self.create_user_and_login(organization=org)
        results = self.app.get(f"/api/collaboration/{col.id}/organization",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # global permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(organization=org, rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}/organization",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # organization permissions of another organization
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION,
                            Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}/organization",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # now with the correct organization
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION,
                            Operation.VIEW)
        headers = self.create_user_and_login(organization=org, rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}/organization",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_view_collaboration_organization_permissions_as_node(self):

        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        # node of a different organization
        headers = self.create_node_and_login()
        results = self.app.get(f"/api/collaboration/{col.id}/organization",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # node of the correct organization
        headers = self.create_node_and_login(organization=org,
                                             collaboration=col)
        results = self.app.get(f"/api/collaboration/{col.id}/organization",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_view_collaboration_organization_permissions_as_container(self):

        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        # node of a different organization
        headers = self.login_container()
        results = self.app.get(f"/api/collaboration/{col.id}/organization",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        headers = self.login_container(organization=org, collaboration=col)
        results = self.app.get(f"/api/collaboration/{col.id}/organization",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_edit_collaboration_organization_permissions(self):

        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        org2 = Organization()
        org2.save()

        # try to do it without permission
        headers = self.create_user_and_login()
        results = self.app.post(f"/api/collaboration/{col.id}/organization",
                                headers=headers, json={'id': org2.id})
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # edit permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.post(f"/api/collaboration/{col.id}/organization",
                                headers=headers, json={'id': org2.id})
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), 2)

    def test_delete_collaboration_organization_pesmissions(self):

        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        # try to do it without permission
        headers = self.create_user_and_login()
        results = self.app.delete(f"/api/collaboration/{col.id}/organization",
                                  headers=headers, json={'id': org.id})
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # delete it!
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.delete(f"/api/collaboration/{col.id}/organization",
                                  headers=headers, json={'id': org.id})
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json, [])

    def test_view_collaboration_node_permissions(self):

        org = Organization()
        col = Collaboration(organizations=[org])
        node = Node(collaboration=col, organization=org)
        node.save()

        # try to view an non-existant collaboration
        headers = self.create_user_and_login()
        results = self.app.get("/api/collaboration/9999/node", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # try to view without any permissions
        results = self.app.get(f"/api/collaboration/{col.id}/node",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view from another organzization
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION,
                            Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}/node",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view from another organization with global permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL,
                            Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}/node",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), len(col.nodes))

        # try to view from your organization
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION,
                            Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule], organization=org)
        results = self.app.get(f"/api/collaboration/{col.id}/node",
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        node.delete()

    def test_add_collaboration_node_permissions(self):

        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()
        node = Node(organization=org)
        node.save()

        # try non-existant collaboration
        headers = self.create_user_and_login()

        results = self.app.post('/api/collaboration/9999/node',
                                headers=headers, json={'id': node.id})
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # try without proper permissions
        results = self.app.post(f'/api/collaboration/{col.id}/node',
                                headers=headers, json={'id': node.id})
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to add non-existing node
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.post(f'/api/collaboration/{col.id}/node',
                                headers=headers, json={'id': 9999})
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # add a node!
        results = self.app.post(f'/api/collaboration/{col.id}/node',
                                headers=headers, json={'id': node.id})
        self.assertEqual(results.status_code, HTTPStatus.CREATED)
        self.assertEqual(len(results.json), len(col.nodes))

        # try to add a node thats already in there
        results = self.app.post(f'/api/collaboration/{col.id}/node',
                                headers=headers, json={'id': node.id})
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # cleanup
        node.delete()

    def test_delete_collaboration_node_permissions(self):

        org = Organization()
        col = Collaboration(organizations=[org])
        node = Node(organization=org, collaboration=col)
        node.save()

        # try non-existant collaboration
        headers = self.create_user_and_login()
        results = self.app.delete('/api/collaboration/9999/node',
                                  headers=headers, json={'id': node.id})
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # try without proper permissions
        results = self.app.delete(f'/api/collaboration/{col.id}/node',
                                  headers=headers, json={'id': node.id})
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to add non-existing node
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.delete(f'/api/collaboration/{col.id}/node',
                                  headers=headers, json={'id': 9999})
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # try to add a node thats not in there
        node2 = Node()
        node2.save()
        results = self.app.delete(f'/api/collaboration/{col.id}/node',
                                  headers=headers, json={'id': node2.id})
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # delete a node!
        results = self.app.delete(f'/api/collaboration/{col.id}/node',
                                  headers=headers, json={'id': node.id})
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        node.delete()
        node2.delete()

    def test_view_collaboration_task_permissions_as_user(self):

        org = Organization()
        col = Collaboration(organizations=[org])
        task = Task(collaboration=col)
        task.save()

        # view non existing collaboration
        headers = self.create_user_and_login()
        results = self.app.get('/api/collaboration/9999/task',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # view without any permission
        results = self.app.get(f'/api/collaboration/{col.id}/task',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # view from another organization
        rule = Rule.get_by_("task", Scope.ORGANIZATION,
                            Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f'/api/collaboration/{col.id}/task',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # view from your own organization
        headers = self.create_user_and_login(rules=[rule], organization=org)
        results = self.app.get(f'/api/collaboration/{col.id}/task',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), len(col.tasks))

        # view with global permissions
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f'/api/collaboration/{col.id}/task',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), len(col.tasks))

    def test_view_collaboration_task_permissions_as_node(self):

        org = Organization()
        col = Collaboration(organizations=[org])
        node, api_key = self.create_node(org, col)
        task = Task(collaboration=col)
        task.save()

        headers = self.login_node(api_key)
        results = self.app.get(f'/api/collaboration/{col.id}/task',
                               headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        node.delete()

    def test_view_node_permissions_as_user(self):

        org = Organization()
        col = Collaboration(organizations=[org])
        node = Node(organization=org, collaboration=col)
        node.save()

        # view non existing node
        headers = self.create_user_and_login()
        results = self.app.get('/api/node/9999', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # missing permissions
        results = self.app.get(f'/api/node/{node.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # organization permissions
        rule1 = Rule.get_by_("node", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.create_user_and_login(organization=org, rules=[rule1])
        results = self.app.get(f'/api/node/{node.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # organization permissions from another organization
        headers = self.create_user_and_login(rules=[rule1])
        results = self.app.get(f'/api/node/{node.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # global permissions
        rule2 = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule2])
        results = self.app.get(f'/api/node/{node.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # list organization permissions
        headers = self.create_user_and_login(organization=org, rules=[rule1])
        results = self.app.get('/api/node', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), len(col.nodes))

        # list global permissions
        headers = self.create_user_and_login(rules=[rule2])
        results = self.app.get('/api/node', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), len(Node.get()))

        # cleanup
        node.delete()

    def test_view_node_permissions_as_node(self):

        org = Organization()
        col = Collaboration(organizations=[org])
        node, api_key = self.create_node(org, col)

        headers = self.login_node(api_key)

        # global permissions
        results = self.app.get(f'/api/node/{node.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # list organization permissions
        results = self.app.get('/api/node', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), len(org.nodes))

        # cleanup
        node.delete()

    def test_create_node_permissions(self):

        org = Organization()
        col = Collaboration(organizations=[org])
        org2 = Organization()
        org2.save()

        # test non existing collaboration
        headers = self.create_user_and_login()
        results = self.app.post('/api/node', headers=headers,
                                json={'collaboration_id': 9999})
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test creating a node without any permissions
        headers = self.create_user_and_login()
        results = self.app.post('/api/node', headers=headers,
                                json={'collaboration_id': col.id})
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # testing creating a node with organization permissions and supplying
        # an organization id
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.CREATE)
        headers = self.create_user_and_login(organization=org, rules=[rule])
        results = self.app.post('/api/node', headers=headers, json={
            'collaboration_id': col.id,
            'organization_id': org.id
        })

        self.assertEqual(results.status_code, HTTPStatus.CREATED)
        node_id = results.json.get('id')
        results = self.app.post('/api/node', headers=headers, json={
            'collaboration_id': col.id,
            'organization_id': org2.id  # <-------
        })
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test adding a node to an collaboration from an organization witch
        # does not belong to the collaboration
        headers = self.create_user_and_login(organization=org2, rules=[rule])
        results = self.app.post('/api/node', headers=headers, json={
            'collaboration_id': col.id
        })
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # check an creating an already existing node
        headers = self.create_user_and_login(organization=org, rules=[rule])
        results = self.app.post('/api/node', headers=headers, json={
            'collaboration_id': col.id
        })
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # lets retry that
        node = Node.get(node_id)
        node.delete()
        results = self.app.post('/api/node', headers=headers, json={
            'collaboration_id': col.id
        })
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # test global permissions
        col.organizations.append(org2)
        col.save()
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.CREATE)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.post('/api/node', headers=headers, json={
            'collaboration_id': col.id,
            'organization_id': org2.id
        })
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

    def test_delete_node_permissions(self):

        org = Organization()
        col = Collaboration(organizations=[org])
        node = Node(organization=org, collaboration=col)
        node.save()

        # unexisting node
        headers = self.create_user_and_login()
        results = self.app.delete('/api/node/9999', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # organization permission other organization
        rule = Rule.get_by_('node', Scope.ORGANIZATION, Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.delete(f'/api/node/{node.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # organization permission
        rule = Rule.get_by_('node', Scope.ORGANIZATION, Operation.DELETE)
        headers = self.create_user_and_login(organization=org, rules=[rule])
        results = self.app.delete(f'/api/node/{node.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # global permission
        node2 = Node(organization=org, collaboration=col)
        node2.save()
        rule = Rule.get_by_('node', Scope.GLOBAL, Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.delete(f'/api/node/{node2.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_patch_node_permissions_as_user(self):
        # test patching non-existant node
        headers = self.create_user_and_login()
        results = self.app.patch("/api/node/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test user without any permissions
        org = Organization()
        col = Collaboration(organizations=[org])
        node = Node(organization=org, collaboration=col)
        node.save()

        results = self.app.patch(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test user with global permissions
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.EDIT)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.patch(f"/api/node/{node.id}", headers=headers,
                                 json={"name": "A"})
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json['name'], "A")

        # test user with org permissions and own organization
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.EDIT)
        headers = self.create_user_and_login(org, [rule])
        results = self.app.patch(f"/api/node/{node.id}", headers=headers,
                                 json={'name': 'B'})
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json['name'], "B")

        # test user with org permissions and other organization
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.patch(f"/api/node/{node.id}", headers=headers,
                                 json={'name': 'C'})
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test updatin the `organization_id` with organization permissions
        org2 = Organization()
        org2.save()
        results = self.app.patch(f"/api/node/{node.id}", headers=headers,
                                 json={'organization_id': org2.id})
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test assigning it to a node thats not part of the collaborat
        col2 = Collaboration(organizations=[org2])
        col2.save()
        results = self.app.patch(f"/api/node/{node.id}", headers=headers,
                                 json={'collaboration_id': col2.id})
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # collaboration_id and organization_id. Note that the organization
        # is assigned before the collaboration is defined.
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.EDIT)
        headers = self.create_user_and_login(org2, rules=[rule])
        results = self.app.patch(f'/api/node/{node.id}', headers=headers,
                                 json={'collaboration_id': col2.id,
                                       'organization_id': org2.id})
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json['organization']['id'], org2.id)
        self.assertEqual(results.json['collaboration']['id'], col2.id)

        # try to patch the node's VPN IP address
        results = self.app.patch(f'/api/node/{node.id}', headers=headers,
                                 json={'ip': '0.0.0.0'})
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json['ip'], '0.0.0.0')

        # assign unknow organization
        results = self.app.patch(f'/api/node/{node.id}', headers=headers,
                                 json={'organization_id': 9999})
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # cleanup
        node.delete()

    def test_view_task_permissions_as_user(self):
        # non existing task
        headers = self.create_user_and_login()
        results = self.app.get('/api/task/9999', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test user without any permissions and id
        org = Organization()
        col = Collaboration(organizations=[org])
        task = Task(name="unit", collaboration=col)
        task.save()

        results = self.app.get(f'/api/task/{task.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test user with org permissions with id
        rule = Rule.get_by_("task", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.create_user_and_login(org, rules=[rule])
        results = self.app.get(f'/api/task/{task.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json['name'], 'unit')

        # test user with org permissions with id from another org
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f'/api/task/{task.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test user with org permissions without id
        headers = self.create_user_and_login(org, rules=[rule])
        results = self.app.get('/api/task', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test user with global permissions and id
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.get(f'/api/task/{task.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test user with global permissions without id
        results = self.app.get('/api/task', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_view_task_permissions_as_node_and_container(self):
        # test node with id
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()
        task = Task(collaboration=col, image="some-image")
        task.save()
        res = Result(task=task)
        res.save()

        headers = self.create_node_and_login(organization=org)
        results = self.app.get(f'/api/task/{task.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test node without id
        results = self.app.get('/api/task', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test container with id
        headers = self.login_container(collaboration=col, organization=org,
                                       task=task)
        results = self.app.get(f'/api/task/{task.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test container without id
        results = self.app.get('/api/task', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_create_task_permission_as_user(self):
        # non existant collaboration
        headers = self.create_user_and_login()
        results = self.app.post('/api/task', headers=headers, json={
            "collaboration_id": 9999
        })
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # organizations outside of collaboration
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        # task without any node created
        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org.id}],
            "collaboration_id": col.id
        })
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # node is used implicitly as in further checks, can only create task
        # if node has been created
        node = Node(organization=org, collaboration=col)

        org2 = Organization()
        org2.save()

        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org2.id}], 'collaboration_id': col.id
        })
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # user without any permissions
        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org.id}],
            "collaboration_id": col.id
        })
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # user with organization permissions for other organization
        rule = Rule.get_by_("task", Scope.ORGANIZATION, Operation.CREATE)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org.id}], 'collaboration_id': col.id
        })
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # user with organization permissions
        headers = self.create_user_and_login(org, rules=[rule])
        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org.id}], 'collaboration_id': col.id
        })
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # user with global permissions but outside of the collaboration. They
        # should *not* be allowed to create a task in a collaboration that
        # they're not a part of
        # TODO add test for user with global permission that creates a task for
        # another organization than their own in the same collaboration
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.CREATE)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org.id}], 'collaboration_id': col.id
        })
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test master task
        rule = Rule.get_by_("task", Scope.ORGANIZATION, Operation.CREATE)
        headers = self.create_user_and_login(org, rules=[rule])
        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org.id}],
            'collaboration_id': col.id,
            'master': True
        })
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # cleanup
        node.delete()

    def test_create_task_permissions_as_container(self):
        org = Organization()
        col = Collaboration(organizations=[org])
        parent_task = Task(collaboration=col, image="some-image")
        parent_task.save()
        parent_res = Result(organization=org, task=parent_task)
        parent_res.save()

        # test wrong image name
        headers = self.login_container(collaboration=col, organization=org,
                                       task=parent_task)
        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org.id}],
            'collaboration_id': col.id,
            'image': 'other-image'
        })

        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test other collaboration_id
        col2 = Collaboration(organizations=[org])
        col2.save()
        node2 = Node(organization=org, collaboration=col2)
        node2.save()
        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org.id}],
            'collaboration_id': col2.id,
            'image': 'some-image'
        })
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test with correct parameters
        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org.id}],
            'collaboration_id': col.id,
            'image': 'some-image'
        })
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # test already completed task
        parent_res.finished_at = datetime.date(2020, 1, 1)
        parent_res.save()
        results = self.app.post('/api/task', headers=headers, json={
            "organizations": [{'id': org.id}],
            'collaboration_id': col.id,
            'image': 'some-image'
        })
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        node2.delete()

    def test_delete_task_permissions(self):

        # test non-existing task
        headers = self.create_user_and_login()
        self.app.delete('/api/task/9999', headers=headers)

        # test with organization permissions from other organization
        org = Organization()
        col = Collaboration(organizations=[org])
        task = Task(collaboration=col)
        task.save()

        rule = Rule.get_by_("task", Scope.ORGANIZATION, Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.delete(f'/api/task/{task.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test with organization permissions
        headers = self.create_user_and_login(org, [rule])
        results = self.app.delete(f'/api/task/{task.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test with global permissions
        task = Task(collaboration=col)
        task.save()
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.DELETE)
        headers = self.create_user_and_login(rules=[rule])
        results = self.app.delete(f'/api/task/{task.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test that all results are also deleted
        task = Task(collaboration=col)
        res = Result(task=task)
        res.save()
        result_id = res.id  # cannot access this after deletion
        results = self.app.delete(f'/api/task/{task.id}', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertIsNone(Task.get(result_id))

    def test_view_task_result_permissions_as_user(self):

        # non-existing task
        headers = self.create_user_and_login()
        result = self.app.get('/api/task/9999/result', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # test with organization permissions from other organization
        org = Organization()
        col = Collaboration(organizations=[org])
        task = Task(collaboration=col)
        # NB: node is used implicitly in task/{id}/result schema
        node = Node(organization=org, collaboration=col)
        res = Result(task=task, organization=org)
        res.save()

        rule = Rule.get_by_("result", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.get(f'/api/task/{task.id}/result', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test with organization permission
        headers = self.create_user_and_login(org, [rule])
        result = self.app.get(f'/api/task/{task.id}/result', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test with global permission
        rule = Rule.get_by_("result", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.get(f'/api/task/{task.id}/result', headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # cleanup
        node.delete()

    def test_view_task_result_permissions_as_container(self):
        # test if container can
        org = Organization()
        col = Collaboration(organizations=[org])
        task = Task(collaboration=col, image="some-image")
        task.save()
        res = Result(task=task, organization=org)
        res.save()

        headers = self.login_container(collaboration=col, organization=org,
                                       task=task)
        results = self.app.get(f'/api/task/{task.id}/result', headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
