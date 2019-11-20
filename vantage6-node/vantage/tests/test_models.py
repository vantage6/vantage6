import logging
import unittest
import yaml
import bcrypt
import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from vantage.server.controller.fixture import load
from vantage.server.model.base import Database, Base
from vantage.constants import PACAKAGE_FOLDER, APPNAME

from vantage.server.model import (
    Base,
    User,
    Organization,
    Collaboration,
    Task,
    Result,
    Node
)

log = logging.getLogger(__name__.split(".")[-1])
log.level = logging.DEBUG

class TestUserModel(unittest.TestCase):

    def setUp(self):
        Database().connect("sqlite://")
        file_ = str(PACAKAGE_FOLDER / APPNAME / "_data" / "example_fixtures.yaml")
        with open(file_) as f:
            self.entities = yaml.safe_load(f.read())
        load(self.entities, drop_all=True)
        
    def tearDown(self):
        Database().drop_all()

    def test_relations(self):
        organization = self.entities.get("organizations")[0]
        user = organization.get("users")[0]
        db_user = User.getByUsername(user.get("username"))
        self.assertEqual(db_user.organization.name, organization["name"])

    def test_read(self):
        for org in self.entities.get("organizations"):
            for user in org.get("users"):
                db_user = User.getByUsername(user["username"])
                self.assertEqual(db_user.username, user["username"])
                self.assertEqual(db_user.firstname, user["firstname"])
                self.assertEqual(db_user.lastname, user["lastname"])
                self.assertTrue(db_user.check_password(user["password"]))
    
    def test_insert(self):
        db_organization = Organization.get(1)
        user = User(
            username="unit",
            firstname="un",
            lastname="it",
            roles="admin",
            organization=db_organization
        )
        user.set_password("unit_pass")
        user.save()
        db_user = User.getByUsername("unit")
        self.assertEqual(db_user, user)

    def test_methods(self):
        user = self.entities.get("organizations")[0].get("users")[0]
        assert User.getByUsername(user.get("username"))
        assert User.username_exists(user.get("username"))
        assert User.get_user_list()


class TestCollaborationModel(unittest.TestCase):
    def setUp(self):
        Database().connect("sqlite://")
        file_ = str(PACAKAGE_FOLDER / APPNAME / "_data" / "example_fixtures.yaml")
        with open(file_) as f:
            self.entities = yaml.safe_load(f.read())
        load(self.entities, drop_all=True)
        
    def trearDown(self):
        Database().drop_all()

    def test_read(self):
        for col in self.entities.get("collaborations"):
            db_collaboration = Collaboration.find_by_name(col.get("name"))
            assert db_collaboration.name == col.get("name"), "incorrect name"

    def test_insert(self):
        col = Collaboration(
            name="unit_collaboration"
        )
        col.save()
        db_col = Collaboration.find_by_name("unit_collaboration")
        assert db_col == col, "Collaboration not correct stored in the database"

    def test_methods(self):
        db_col = Collaboration.get(1)
        org_ids = db_col.get_organization_ids()
        self.assertIsInstance(org_ids, list)
        self.assertIsInstance(db_col.get_task_ids(), list)
        for node in db_col.get_nodes_from_organizations(org_ids):
            self.assertIsInstance(node, Node)
    
    def test_relations(self):
        db_col = Collaboration.get(1)
        for node in db_col.nodes:
            self.assertIsInstance(node,Node)
        for organization in db_col.organizations:
            self.assertIsInstance(organization, Organization)


class TestNodeModel(unittest.TestCase):
    def setUp(self):
        Database().connect("sqlite://")
        file_ = str(PACAKAGE_FOLDER / APPNAME / "_data" / "example_fixtures.yaml")
        with open(file_) as f:
            self.entities = yaml.safe_load(f.read())
        load(self.entities, drop_all=True)
        
    def trearDown(self):
        Database().drop_all()

    def test_read(self):
        for node in Node.get():
            self.assertIsInstance(node.name, str)
            self.assertIsInstance(node.api_key, str)

    def test_insert(self):
        collaboration = Collaboration.get(1)
        organization = collaboration.organizations[0]
        node = Node(
            name="unit_node",
            api_key="that-we-never-use",
            collaboration=collaboration,
            organization=organization
        )
        node.save()

        node = Node.get_by_api_key("that-we-never-use")
        self.assertIsNotNone(node)
        self.assertIsInstance(node,Node)
        self.assertEqual(node.name, "unit_node", "names do not match")
        self.assertEqual(node.api_key, "that-we-never-use", "api-keys are messed up")
        self.assertEqual(node.collaboration, collaboration, "collaboration do not match")
        self.assertEqual(node.organization, organization, "names do not match")

    def test_methods(self):
        node = Node.get()[0]
        self.assertIsInstance(Node.get_by_api_key(node.api_key), Node)
    
    def test_relations(self):
        node = Node.get()[0]
        self.assertIsNotNone(node)
        self.assertIsInstance(node.organization, Organization)
        self.assertIsInstance(node.collaboration, Collaboration)
        for organization in node.collaboration.organizations:
            self.assertIsInstance(organization, Organization)
            for user in organization.users:
                self.assertIsInstance(user, User)


class TestOrganizationModel(unittest.TestCase):
    def setUp(self):
        Database().connect("sqlite://")
        file_ = str(PACAKAGE_FOLDER / APPNAME / "_data" / "example_fixtures.yaml")
        with open(file_) as f:
            self.entities = yaml.safe_load(f.read())
        load(self.entities, drop_all=True)
        
    def trearDown(self):
        Database().drop_all()

    def test_read(self):
        for organization in self.entities.get("organizations"):
            org = Organization.get_by_name(organization.get("name"))
            self.assertEqual(org.name, organization.get("name"))
            self.assertEqual(org.domain, organization.get("domain"))
            self.assertEqual(org.address1, organization.get("address1"))
            self.assertEqual(org.address2, organization.get("address2"))
            self.assertEqual(org.zipcode, str(organization.get("zipcode")))
            self.assertEqual(org.country, organization.get("country"))

            for user in organization.get("users"):
                db_user = User.getByUsername(user.get("username"))
                self.assertIsNotNone(db_user)
                self.assertEqual(db_user.organization.name, organization.get("name"))

    def test_insert(self):
        col = Collaboration.get()
        org = Organization(
            name="unit_organization",
            domain="testers.com",
            address1="memorylane 1",
            zipcode="bla",
            country="RAM",
            collaborations=col
        )
        org.save()

        db_org = Organization.get_by_name("unit_organization")
        self.assertEqual(db_org, org)

    def test_methods(self):
        name = self.entities.get("organizations")[0].get("name")
        self.assertIsNotNone(Organization.get_by_name(name))

    def test_relations(self):
        for organization in Organization.get():
            for node in organization.nodes:
                self.assertIsInstance(node, Node)
            for collaboration in organization.collaborations:
                self.assertIsInstance(collaboration, Collaboration)
            for user in organization.users:
                self.assertIsInstance(user, User)
            for result in organization.results:
                self.assertIsInstance(result, Result)


class TestResultModel(unittest.TestCase):
    def setUp(self):
        Database().connect("sqlite://")
        file_ = str(PACAKAGE_FOLDER / APPNAME / "_data" / "example_fixtures.yaml")
        with open(file_) as f:
            self.entities = yaml.safe_load(f.read())
        load(self.entities, drop_all=True)
        
    def trearDown(self):
        Database().drop_all()

    def test_read(self):
        for result in Result.get():
            self.assertIsInstance(result, Result)
            self.assertIsNone(result.result)
            self.assertIsInstance(result.assigned_at, datetime.datetime)
            self.assertIsNone(result.started_at)
            self.assertIsNone(result.finished_at)

    def test_insert(self):
        task = Task(name="unit_task")
        result = Result(
            task = task,
            organization=Organization.get()[0],
            input="something"
        )
        result.save()
        self.assertEqual(result, result)


    def test_methods(self):
        for result in Result.get():
            self.assertFalse(result.complete)

    def test_relations(self):
        result = Result.get()[0]
        self.assertIsInstance(result.organization, Organization)
        for user in result.organization.users:
            self.assertIsInstance(user, User)
        self.assertIsInstance(result.task, Task)


class TestTaskModel(unittest.TestCase):
    def setUp(self):
        Database().connect("sqlite://")
        file_ = str(PACAKAGE_FOLDER / APPNAME / "_data" / "example_fixtures.yaml")
        with open(file_) as f:
            self.entities = yaml.safe_load(f.read())
        load(self.entities, drop_all=True)
        
    def trearDown(self):
        Database().drop_all()

    def test_read(self):
        db_tasks = Task.get()
        for task in db_tasks:
            self.assertIsInstance(task, Task)
            self.assertIsInstance(task.name, str)
            # self.assertIsInstance(task.description, str)
            self.assertIsInstance(task.image, str)
            self.assertIsInstance(task.collaboration, Collaboration)
            self.assertIsInstance(task.run_id, int)
            # self.assertIsInstance(task.database, str)
            for result in task.results:
                self.assertIsInstance(result, Result)

    def test_insert(self):
        task = Task(name="unit_task")
        task.save()
        for task in Task.get():
            if task.name == "unit_task":
                db_task = task
                break                
        self.assertEqual(task, db_task)

    def test_methods(self):
        highest_id = 0
        for task in Task.get():
            if task.id > highest_id:
                highest_id = task.id

    def test_relations(self):
        db_task = Task.get()
        for task in db_task:
            self.assertIsInstance(task, Task)
            self.assertIsInstance(task.collaboration, Collaboration)
            for result in task.results:
                self.assertIsInstance(result, Result)
            for result in task.results:
                self.assertIsInstance(result, Result)
            for user in task.collaboration.organizations[0].users:
                self.assertIsInstance(user, User)