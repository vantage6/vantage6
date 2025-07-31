import datetime
import logging
import uuid

from sqlalchemy.exc import IntegrityError

from vantage6.backend.common import session

from vantage6.server.model import (
    Collaboration,
    Node,
    Organization,
    Role,
    Rule,
    Run,
    Task,
    User,
)
from vantage6.server.model.rule import Operation, Scope

from .test_model_base import TestModelBase

log = logging.getLogger(__name__.split(".")[-1])
log.level = logging.CRITICAL
logging.basicConfig(level=logging.CRITICAL)


class TestUserModel(TestModelBase):
    def test_relations(self):
        org = Organization()
        org.save()
        user = User(organization=org)
        user.save()

        db_user = User.get_by_username(user.get("username"))
        self.assertEqual(db_user.organization.name, org.name)

    def test_read(self):
        user = User(
            username="test_user",
        )
        user.save()
        db_user = User.get_by_username(user.username)
        self.assertEqual(db_user.username, user.username)

    def test_insert(self):
        db_organization = Organization.get(1)
        user = User(
            username="unit",
            organization=db_organization,
        )
        user.save()
        db_user = User.get_by_username("unit")
        self.assertEqual(db_user, user)

    def test_methods(self):
        """ "Test model methods."""
        username = str(uuid.uuid4())
        user = User(username=username)
        user.save()
        assert User.get_by_username(username)
        assert User.username_exists(username)

    def test_duplicate_user(self):
        """Duplicate usernames are not permitted."""
        # print(User.get())
        user1 = User(username="duplicate-user")
        user1.save()

        user2 = User(username="duplicate-user")
        self.assertRaises(IntegrityError, user2.save)

        session.session.remove()


class TestCollaborationModel(TestModelBase):
    def test_read(self):
        col = Collaboration(name=str(uuid.uuid4()))
        col.save()
        db_collaboration = Collaboration.find_by_name(col.name)
        self.assertEqual(db_collaboration.name, col.name)

    def test_insert(self):
        col = Collaboration(name="unit_collaboration")
        col.save()
        db_col = Collaboration.find_by_name("unit_collaboration")
        self.assertEqual(db_col, col)

    def test_methods(self):
        db_col = Collaboration(name=str(uuid.uuid4()))
        db_col.save()
        org_ids = db_col.get_organization_ids()
        self.assertIsInstance(org_ids, list)
        self.assertIsInstance(db_col.get_task_ids(), list)
        for node in db_col.get_nodes_from_organizations(org_ids):
            self.assertIsInstance(node, Node)

    def test_relations(self):
        db_col = Collaboration.get(1)
        for node in db_col.nodes:
            self.assertIsInstance(node, Node)
        for organization in db_col.organizations:
            self.assertIsInstance(organization, Organization)


class TestNodeModel(TestModelBase):
    def test_read(self):
        for node in Node.get():
            self.assertIsInstance(node.name, str)

    def test_insert(self):
        org = Organization(name=str(uuid.uuid4()))
        collaboration = Collaboration(name=str(uuid.uuid4()), organizations=[org])
        collaboration.save()
        node = Node(
            name="unit_node",
            collaboration=collaboration,
            organization=org,
            keycloak_id="1234567890111",
        )
        node.save()

        node = Node.get_by_keycloak_id("1234567890111")
        self.assertIsNotNone(node)
        self.assertIsInstance(node, Node)
        self.assertEqual(node.name, "unit_node")
        self.assertEqual(node.collaboration, collaboration)
        self.assertEqual(node.organization, org)

    def test_methods(self):
        node = Node(name="la chuck", keycloak_id="1234567890")
        node.save()
        self.assertIsInstance(Node.get_by_keycloak_id("1234567890"), Node)

    def test_relations(self):
        org = Organization(name=str(uuid.uuid4()))
        col = Collaboration(name=str(uuid.uuid4()), organizations=[org])
        node = Node(collaboration=col, organization=org)
        node.save()
        self.assertIsNotNone(node)
        self.assertIsInstance(node.organization, Organization)
        self.assertIsInstance(node.collaboration, Collaboration)
        for organization in node.collaboration.organizations:
            self.assertIsInstance(organization, Organization)
            for user in organization.users:
                self.assertIsInstance(user, User)


class TestOrganizationModel(TestModelBase):
    def test_read(self):
        org = Organization(
            name=str(uuid.uuid4()),
            domain=str(uuid.uuid4()),
            address1=str(uuid.uuid4()),
            address2=str(uuid.uuid4()),
            zipcode=str(uuid.uuid4()),
        )
        org.save()
        username = str(uuid.uuid4())
        user = User(organization=org, username=username)
        user.save()

        db_org = Organization.get_by_name(org.name)

        self.assertEqual(db_org.name, org.name)
        self.assertEqual(db_org.domain, org.domain)
        self.assertEqual(db_org.address1, org.address1)
        self.assertEqual(db_org.address2, org.address2)
        self.assertEqual(db_org.zipcode, org.zipcode)
        self.assertEqual(db_org.country, org.country)

        for user in db_org.users:
            db_user = User.get_by_username(username)
            self.assertIsNotNone(db_user)
            self.assertEqual(db_user.organization.name, org.name)

    def test_insert(self):
        col = Collaboration.get()
        org = Organization(
            name="unit_organization",
            domain="testers.com",
            address1="memorylane 1",
            zipcode="bla",
            country="RAM",
            collaborations=col,
        )
        org.save()

        db_org = Organization.get_by_name("unit_organization")
        self.assertEqual(db_org, org)

    def test_methods(self):
        org = Organization(name=str(uuid.uuid4()))
        org.save()
        name = org.name
        self.assertIsNotNone(Organization.get_by_name(name))

    def test_relations(self):
        for organization in Organization.get():
            for node in organization.nodes:
                self.assertIsInstance(node, Node)
            for collaboration in organization.collaborations:
                self.assertIsInstance(collaboration, Collaboration)
            for user in organization.users:
                self.assertIsInstance(user, User)
            for run in organization.runs:
                self.assertIsInstance(run, Run)


class TestRunModel(TestModelBase):
    def test_read(self):
        for run in Run.get():
            self.assertIsInstance(run, Run)
            self.assertIsNone(run.result)
            self.assertIsInstance(run.assigned_at, datetime.datetime)
            self.assertIsNone(run.started_at)
            self.assertIsNone(run.finished_at)

    def test_insert(self):
        org = Organization(name=str(uuid.uuid4()))
        org.save()
        task = Task(name="unit_task")
        run = Run(task=task, organization=org, arguments="something")
        run.save()
        self.assertEqual(run, run)

    # def test_methods(self):
    #     for result in Result.get():
    #         self.assertFalse(result.complete)

    def test_relations(self):
        org = Organization(name=str(uuid.uuid4()))
        col = Collaboration(name=str(uuid.uuid4()), organizations=[org])
        task = Task(name="unit_task", collaboration=col)
        run = Run(task=task, organization=org)
        run.save()
        self.assertIsInstance(run.organization, Organization)
        for user in run.organization.users:
            self.assertIsInstance(user, User)
        self.assertIsInstance(run.task, Task)


class TestTaskModel(TestModelBase):
    def test_read(self):
        db_tasks = Task.get()
        for task in db_tasks:
            self.assertIsInstance(task, Task)
            self.assertIsInstance(task.name, str)
            # self.assertIsInstance(task.description, str)
            self.assertIsInstance(task.image, str)
            self.assertIsInstance(task.collaboration, Collaboration)
            self.assertIsInstance(task.job_id, int)
            # self.assertIsInstance(task.database, str)
            for run in task.runs:
                self.assertIsInstance(run, Run)

    def test_insert(self):
        col = Collaboration(name=str(uuid.uuid4()))
        col.save()
        task = Task(
            name="unit_task",
            image="some-image",
            collaboration=col,
            job_id=1,
        )
        task.save()
        db_task = None
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
        org = Organization(name=str(uuid.uuid4()))
        col = Collaboration(name=str(uuid.uuid4()), organizations=[org])
        col.save()
        task = Task(
            name="unit_task",
            collaboration=col,
            runs=[Run(organization=org)],
        )
        task.save()
        db_task = Task.get()
        for task in db_task:
            self.assertIsInstance(task, Task)
            self.assertIsInstance(task.collaboration, Collaboration)
            for run in task.runs:
                self.assertIsInstance(run, Run)


class TestRuleModel(TestModelBase):
    def test_read(self):
        rule = Rule(
            name="some-name", operation=Operation.CREATE.value, scope=Scope.GLOBAL
        )
        rule.save()

        rules = Rule.get()

        # check that there are rules
        self.assertTrue(rules)
        # check their type
        for rule in rules:
            self.assertIsInstance(rule, Rule)

    # def test_insert(self):
    #     rule = Rule(
    #         name="unittest",
    #         description="A unittest rule",
    #         scope=Scope.OWN,
    #         operation=Operation.CREATE
    #     )
    #     rule.save()

    def test_methods(self):
        # check that error is raised
        self.assertIsNone(Rule.get_by_("non-existent", Scope.GLOBAL, Operation.CREATE))

    def test_relations(self):
        rules = Rule.get()
        for rule in rules:
            self.assertIsInstance(rule.name, str)
            self.assertIn(rule.operation, Operation.list())
            self.assertIn(rule.scope, Scope.list())

            for role in rule.roles:
                self.assertIsInstance(role, Role)

            for user in rule.users:
                self.assertIsInstance(user, User)
