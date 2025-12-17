import logging
from http import HTTPStatus
from unittest.mock import patch

from vantage6.common import logger_name

from vantage6.server.model import (
    AlgorithmStore,
    Collaboration,
    Organization,
    Rule,
)
from vantage6.server.model.rule import Operation, Scope

from .test_resource_base import TestResourceBase

logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):
    @patch("vantage6.server.algo_store_communication._check_algorithm_store_online")
    def test_create_algorithm_store_record(self, mock_check_algorithm_store_online):
        mock_check_algorithm_store_online.return_value = True

        """Test creating an algorithm store record"""
        # initialize resources
        org = Organization()
        col = Collaboration(organizations=[org])
        col.save()
        headers = self.get_user_auth_header(organization=org)

        record = {
            "name": "test",
            "algorithm_store_url": "http://test.com",
            "collaboration_id": col.id,
        }

        # test creating a record without any permissions
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test creating a record with collaboration permissions if not member
        # of the collaboration
        rule = Rule.get_by_("collaboration", Scope.COLLABORATION, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test creating a record with collaboration permissions if member
        # of the collaboration
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # test that doing it again fails because the record already exists
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # test that we cannot create a record for all collaborations with
        # collaboration permissions
        del record["collaboration_id"]
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test creating a record with global permissions. Note that while we
        # are creating the same algorithm store record, we are doing it for
        # all collaborations, so it should succeed
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # cleanup
        org.delete()
        col.delete()
        for resource in AlgorithmStore.get():
            resource.delete()

    def test_view_algorithm_store(self):
        """Test viewing algorithm store records"""
        # without permissions
        headers = self.get_user_auth_header()
        results = self.app.get("/api/algorithmstore", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # view with organization permissions
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        col.save()
        algo_store = AlgorithmStore(
            name="test", url="http://test.com", api_path="/api", collaboration=col
        )
        algo_store.save()
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])

        # list. We expect to find all stores without specified collaboration and this one
        results = self.app.get("/api/algorithmstore", headers=headers)
        all_stores = AlgorithmStore.get()
        num_stores_to_find = (
            len([store for store in all_stores if store.collaboration_id is None]) + 1
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), num_stores_to_find)
        # single record
        results = self.app.get(f"/api/algorithmstore/{algo_store.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # view with another organization within the same collaboration
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        results = self.app.get(
            "/api/algorithmstore",
            headers=headers,
            query_string={"collaboration_id": col.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), num_stores_to_find)
        results = self.app.get(f"/api/algorithmstore/{algo_store.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view with organization permissions but not member of
        # collaboration
        org3 = Organization()
        org3.save()
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        results = self.app.get(f"/api/algorithmstore/{algo_store.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # view with global permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.get("/api/algorithmstore", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), len(AlgorithmStore.get()))

        results = self.app.get(f"/api/algorithmstore/{algo_store.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()
        algo_store.delete()

    def test_patch_algorithm_store(self):
        """Test patching algorithm store records"""
        # initialize resources
        org = Organization()
        col = Collaboration(organizations=[org])
        col.save()
        algo_store = AlgorithmStore(
            name="test", url="http://test.com", api_path="/api", collaboration=col
        )
        algo_store.save()

        # test patching without any permissions
        headers = self.get_user_auth_header()
        results = self.app.patch(
            f"/api/algorithmstore/{algo_store.id}",
            headers=headers,
            json={"name": "test1"},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test patching non-existing record
        rule = Rule.get_by_("collaboration", Scope.COLLABORATION, Operation.EDIT)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.patch("/api/algorithmstore/9999", headers=headers, json={})
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test patching with collaboration permissions
        results = self.app.patch(
            f"/api/algorithmstore/{algo_store.id}",
            headers=headers,
            json={"name": "test2"},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "test2")

        # test patching with global permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.patch(
            f"/api/algorithmstore/{algo_store.id}",
            headers=headers,
            json={"name": "test3"},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "test3")

        # cleanup
        org.delete()
        col.delete()
        algo_store.delete()

    def test_delete_algorithm_store(self):
        """Test deleting algorithm store records"""
        # initialize resources
        org = Organization()
        col = Collaboration(organizations=[org])
        col.save()
        algo_store = AlgorithmStore(
            name="test",
            url="http://test.com",
            api_path="/api",
            collaboration_id=col.id,
        )
        algo_store.save()

        # test deleting without any permissions
        headers = self.get_user_auth_header()
        results = self.app.delete(
            f"/api/algorithmstore/{algo_store.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test deleting non-existing record
        rule = Rule.get_by_("collaboration", Scope.COLLABORATION, Operation.EDIT)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.delete("/api/algorithmstore/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test deleting with collaboration permissions
        results = self.app.delete(
            f"/api/algorithmstore/{algo_store.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test deleting with global permissions
        algo_store = AlgorithmStore(
            name="test2",
            url="http://test.com",
            api_path="/api",
            collaboration_id=col.id,
        )
        algo_store.save()
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(
            f"/api/algorithmstore/{algo_store.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        col.delete()
