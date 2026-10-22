import tempfile
import unittest
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import yaml
from click.testing import CliRunner
from kubernetes.client.exceptions import ApiException

from vantage6.common.globals import SERVICE_BASED_DATABASE_TYPES

from vantage6.cli.common.remove import _remove_referenced_secrets
from vantage6.cli.common.utils import (
    ensure_referenced_secrets_exist,
    referenced_secret_names,
    store_credentials_in_kubernetes_secrets,
)
from vantage6.cli.configuration_manager import (
    AuthConfigurationManager,
    HQConfigurationManager,
    HubConfigurationManager,
    NodeConfigurationManager,
)
from vantage6.cli.context.node import NodeContext
from vantage6.cli.hub.new import cli_hub_new
from vantage6.cli.hub.utils.credentials import (
    HubCredentials,
    HubSecretNames,
    build_hub_secrets,
    extract_auth_credentials,
    extract_hq_credentials,
    hub_release_name,
    rabbitmq_uri,
)
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.node.new import node_configuration_questionaire
from vantage6.cli.node.set_api_key import cli_node_set_api_key


def _render(manager_class, config: dict, is_sandbox: bool = False) -> str:
    manager = manager_class("test", is_sandbox=is_sandbox)
    manager.put(config)
    return manager.render_config()


HQ_CONFIG = {
    "hq": {"logging": {}},
    "database": {"external": True},
    "rabbitmq": {},
    "ui": {},
    "prometheus": {},
}


class TestTemplatesWithoutDefaultSecrets(unittest.TestCase):
    def test_production_without_secret_fails(self):
        with self.assertRaisesRegex(ValueError, "must be set, or provided via"):
            _render(HQConfigurationManager, HQ_CONFIG)

    def test_production_with_secret_reference_omits_secrets(self):
        config = {**HQ_CONFIG, "hq": {"logging": {}, "existingSecret": "hq-secret"}}
        rendered = yaml.safe_load(_render(HQConfigurationManager, config))
        self.assertEqual(rendered["hq"]["existingSecret"], "hq-secret")
        self.assertNotIn("uri", rendered["database"])
        self.assertNotIn("password", rendered["rabbitmq"])

    def test_production_with_values_renders_them(self):
        config = {
            **HQ_CONFIG,
            "database": {"external": True, "uri": "postgresql://u:pw@db/x"},
            "rabbitmq": {"password": "rabbit-pw"},
        }
        rendered = yaml.safe_load(_render(HQConfigurationManager, config))
        self.assertEqual(rendered["database"]["uri"], "postgresql://u:pw@db/x")
        self.assertEqual(rendered["rabbitmq"]["password"], "rabbit-pw")

    def test_node_namespace_only_rendered_when_set(self):
        config = {
            "node": {
                "apiKey": "key",
                "keycloak": {},
                "hq": {"url": "https://hq.example.org"},
                "databases": {"fileBased": [], "serviceBased": []},
                "logging": {},
                "encryption": {"enabled": False},
                "policies": {},
            }
        }
        rendered = yaml.safe_load(_render(NodeConfigurationManager, config))
        self.assertNotIn("namespace", rendered)
        rendered = yaml.safe_load(
            _render(NodeConfigurationManager, {**config, "namespace": "ns1"})
        )
        self.assertEqual(rendered["namespace"], "ns1")

    def test_node_database_lists_are_never_null(self):
        # the node chart concatenates both lists, which fails if either is null
        node = {
            "apiKey": "key",
            "keycloak": {},
            "hq": {"url": "https://hq.example.org"},
            "logging": {},
            "encryption": {"enabled": False},
            "policies": {},
        }
        file_db = {
            "name": "default",
            "uri": "/data/db.csv",
            "type": "csv",
            "volumePath": "/data",
            "originalName": "db.csv",
        }
        cases = [
            ({"fileBased": [], "serviceBased": []}, 0, 0),
            ({"fileBased": [file_db], "serviceBased": []}, 1, 0),
            (None, 0, 0),
        ]
        for databases, n_file, n_service in cases:
            with self.subTest(databases=databases):
                config = {"node": dict(node)}
                if databases is not None:
                    config["node"]["databases"] = databases
                rendered = yaml.safe_load(_render(NodeConfigurationManager, config))
                rendered_dbs = rendered["node"]["databases"]
                self.assertEqual(len(rendered_dbs["fileBased"]), n_file)
                self.assertEqual(len(rendered_dbs["serviceBased"]), n_service)

    def test_sandbox_uses_defaults(self):
        rendered = yaml.safe_load(
            _render(HQConfigurationManager, HQ_CONFIG, is_sandbox=True)
        )
        self.assertEqual(rendered["rabbitmq"]["password"], "rabbitmquserpassword")


class TestHubCredentials(unittest.TestCase):
    def setUp(self):
        self.names = HubSecretNames.for_hub("myhub", system_folders=False)
        self.credentials = HubCredentials(
            admin_password="SENTINEL_ADMIN", admin_client_secret="SENTINEL_CLIENT"
        )

    def test_secret_names_use_release_name(self):
        self.assertEqual(hub_release_name("myhub", False), "vantage6-myhub-user-hub")
        self.assertEqual(self.names.hq, "vantage6-myhub-user-hub-hq-credentials")

    def test_rabbitmq_uri_is_url_encoded(self):
        self.assertEqual(
            rabbitmq_uri("rel", "p@ss:/w"),
            "amqp://rabbitmquser:p%40ss%3A%2Fw@rel-rabbitmq:5672/%2Fvantage6",
        )

    def test_hub_config_contains_no_secrets(self):
        auth = extract_auth_credentials(
            {
                "keycloak": {
                    "production": True,
                    "publicClient": {},
                    "adminUserSecret": "kc-admin",
                    "smtpServer": {"host": "smtp", "password": "SENTINEL_SMTP"},
                },
                "database": {
                    "external": True,
                    "host": "db",
                    "username": "kc",
                    "password": "SENTINEL_AUTHDB",
                },
            },
            self.credentials,
            self.names,
        )
        hq = extract_hq_credentials(
            {
                **HQ_CONFIG,
                "hq": {"logging": {}},
                "database": {"external": True, "uri": "postgresql://u:SENTINEL@db/x"},
                "rabbitmq": {"password": "SENTINEL_RABBIT"},
            },
            self.credentials,
            self.names,
        )
        hub_config = {
            "hubGateway": {},
            "urls": {
                kind: {"auth": "a", "store": "s", "ui": "u", "hq": "h"}
                for kind in ("external", "internal")
            },
            "keycloak": {"url": "a", "credentialsInSecrets": True},
        }
        manager = HubConfigurationManager("myhub")
        manager.put(hub_config)
        rendered = manager.render_config(
            auth_config=_render(AuthConfigurationManager, auth),
            hq_config=_render(HQConfigurationManager, hq),
        )

        self.assertNotIn("SENTINEL", rendered)
        values = yaml.safe_load(rendered)
        self.assertEqual(values["hq"]["hq"]["existingSecret"], self.names.hq)
        self.assertEqual(
            values["auth"]["database"]["existingSecret"], self.names.auth_db
        )
        self.assertEqual(
            values["auth"]["keycloak"]["realmImport"]["existingSecret"],
            self.names.realm,
        )

        hub_secrets = build_hub_secrets(
            self.credentials, self.names, "rel", has_store=False
        )
        self.assertEqual(
            set(hub_secrets), {self.names.hq, self.names.auth_db, self.names.realm}
        )
        self.assertEqual(
            hub_secrets[self.names.realm],
            {
                "admin-password": "SENTINEL_ADMIN",
                "backend-client-secret": "SENTINEL_CLIENT",
                "smtp-password": "SENTINEL_SMTP",
            },
        )
        self.assertEqual(
            hub_secrets[self.names.auth_db],
            {"username": "kc", "password": "SENTINEL_AUTHDB"},
        )
        hq_secret = hub_secrets[self.names.hq]
        self.assertEqual(hq_secret["V6_DATABASE_URI"], "postgresql://u:SENTINEL@db/x")
        self.assertEqual(hq_secret["RABBITMQ_PASSWORD"], "SENTINEL_RABBIT")
        self.assertEqual(hq_secret["KEYCLOAK_ADMIN_PASSWORD"], "SENTINEL_ADMIN")
        self.assertNotIn("KEYCLOAK_ADMIN_USERNAME", hq_secret)
        self.assertNotIn("KEYCLOAK_ADMIN_CLIENT", hq_secret)
        self.assertTrue(hq_secret["V6_JWT_SECRET_KEY"])


class TestHubWizard(unittest.TestCase):
    """Run `v6 hub new` with mocked questionnaires and Kubernetes."""

    @patch("vantage6.cli.hub.new.store_credentials_in_kubernetes_secrets")
    @patch("vantage6.cli.hub.new._print_credentials_one_time")
    @patch("vantage6.cli.hub.new.algo_store_configuration_questionaire")
    @patch("vantage6.cli.hub.new.hq_configuration_questionaire")
    @patch("vantage6.cli.hub.new.auth_configuration_questionaire")
    @patch("vantage6.cli.hub.new.global_auth_settings_questionaire")
    @patch("vantage6.cli.hub.new._get_base_config")
    @patch("vantage6.cli.hub.new.select_k8s_config")
    @patch("vantage6.cli.hub.new.HubContext.config_exists", return_value=False)
    @patch("vantage6.cli.common.new.select_context_class")
    @patch("vantage6.cli.common.new.ensure_config_dir_writable", return_value=True)
    @patch("vantage6.cli.configuration_create.AppContext.instance_folders")
    def test_hub_config_refers_to_secrets(
        self,
        instance_folders,
        _writable,
        context_class,
        _exists,
        select_k8s_config,
        base_config,
        global_auth,
        auth_q,
        hq_q,
        store_q,
        _print,
        store_credentials,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            instance_folders.return_value = {"config": tmp, "log": tmp}
            context_class.return_value.config_exists.return_value = False
            select_k8s_config.return_value = KubernetesConfig(namespace="ns1")
            base_config.return_value = {
                "hq_url": "https://hq.example.org",
                "auth_url": "https://auth.example.org",
                "ui_url": "https://portal.example.org",
                "store_url": "https://store.example.org",
                "store_name": "store",
                "has_store": True,
                "log_level": "INFO",
            }
            global_auth.return_value = {
                "adminPassword": "SENTINEL_ADMIN",
                "adminClientSecret": "SENTINEL_CLIENT",
            }
            auth_q.return_value = {
                "keycloak": {
                    "production": True,
                    "publicClient": {},
                    "adminUserSecret": "kc-admin",
                    "smtpServer": {
                        "host": "smtp",
                        "port": "587",
                        "from": "a@b.c",
                        "auth": "true",
                        "user": "u",
                        "password": "SENTINEL_SMTP",
                    },
                },
                "database": {
                    "external": True,
                    "host": "db",
                    "username": "kc",
                    "password": "SENTINEL_AUTHDB",
                    "name": "kc",
                },
            }
            hq_q.return_value = {
                "hq": {"keycloak": {}, "logging": {}},
                "database": {"external": True, "uri": "postgresql://u:SENTINEL@db/hq"},
                "ui": {},
                "rabbitmq": {"password": "SENTINEL_RABBIT"},
                "prometheus": {},
            }
            store_q.return_value = {
                "store": {"keycloak": {}, "logging": {}},
                "database": {"external": True, "uri": "postgresql://u:SENTINEL@db/st"},
            }

            result = CliRunner().invoke(cli_hub_new, ["--name", "myhub", "--user"])

            self.assertEqual(result.exit_code, 0, result.output)
            rendered = (Path(tmp) / "myhub.yaml").read_text()

        self.assertNotIn("SENTINEL", rendered)
        values = yaml.safe_load(rendered)
        names = HubSecretNames.for_hub("myhub", system_folders=False)
        self.assertEqual(values["hq"]["hq"]["existingSecret"], names.hq)
        self.assertEqual(values["store"]["store"]["existingSecret"], names.store)
        self.assertEqual(values["auth"]["database"]["existingSecret"], names.auth_db)
        self.assertEqual(
            values["auth"]["keycloak"]["realmImport"]["existingSecret"], names.realm
        )
        self.assertEqual(values["store"]["store"]["smtpServer"]["user"], "u")

        k8s_cfg, hub_secrets = store_credentials.call_args.args
        self.assertEqual(k8s_cfg.namespace, "ns1")
        self.assertEqual(
            set(hub_secrets), {names.hq, names.store, names.auth_db, names.realm}
        )
        self.assertEqual(hub_secrets[names.store]["V6_SMTP_PASSWORD"], "SENTINEL_SMTP")
        self.assertEqual(
            hub_secrets[names.hq]["V6_DATABASE_URI"], "postgresql://u:SENTINEL@db/hq"
        )


class TestNodeSecrets(unittest.TestCase):
    @patch("vantage6.cli.node.new.store_credentials_in_kubernetes_secrets")
    @patch("vantage6.cli.node.new.NodeClient.authenticate")
    @patch("vantage6.cli.node.new.q")
    def test_node_wizard_stores_credentials_in_secret(self, q, _authenticate, store):
        q.unsafe_prompt.side_effect = [
            {"apiKey": "SENTINEL_APIKEY", "hq_url": "https://hq.example.org/"},
            {"port": "443", "api_path": "/hq", "task_dir": "/data"},
        ]
        q.confirm.return_value.unsafe_ask.side_effect = [
            True,  # add a database
            True,  # add an environment variable
            False,  # no more environment variables
            False,  # no more databases
            False,  # no algorithm policies
            False,  # no encryption
        ]
        q.select.return_value.unsafe_ask.side_effect = [
            "Database reachable by URI",
            SERVICE_BASED_DATABASE_TYPES[0],
            "INFO",  # log level
        ]
        q.text.return_value.unsafe_ask.side_effect = [
            "pg-db",  # database label
            "postgresql://u:SENTINEL_DBPW@h/db",  # database URI
            "password",  # environment variable name
            "SENTINEL_DBENV",  # environment variable value
            "https://auth.example.org/",  # keycloak URL
        ]
        k8s_cfg = KubernetesConfig(context="ctx", namespace="ns1")

        config = node_configuration_questionaire(
            "/data", "/log", "mynode", False, k8s_cfg
        )

        secret_name = "vantage6-mynode-user-node-credentials"
        store.assert_called_once_with(
            k8s_cfg,
            {
                secret_name: {
                    "V6_API_KEY": "SENTINEL_APIKEY",
                    "DATABASE_PG_DB_URI": "postgresql://u:SENTINEL_DBPW@h/db",
                    "DATABASE_PG_DB_PASSWORD": "SENTINEL_DBENV",
                }
            },
        )
        rendered = _render(NodeConfigurationManager, config)
        self.assertNotIn("SENTINEL", rendered)
        values = yaml.safe_load(rendered)
        self.assertEqual(values["namespace"], "ns1")
        self.assertEqual(values["node"]["existingSecret"], secret_name)
        self.assertEqual(values["node"]["hq"]["url"], "https://hq.example.org")
        self.assertEqual(values["node"]["keycloak"]["url"], "https://auth.example.org")
        self.assertEqual(
            values["node"]["databases"]["serviceBased"],
            [{"name": "pg-db", "type": SERVICE_BASED_DATABASE_TYPES[0]}],
        )

    @patch("vantage6.cli.node.set_api_key.get_core_api_with_ssl_handling")
    @patch("vantage6.cli.node.set_api_key.update_kubernetes_secret")
    @patch("vantage6.cli.node.set_api_key.ensure_config_dir_writable")
    @patch("vantage6.cli.node.set_api_key.NodeContext")
    def test_set_api_key_updates_secret(self, context, _writable, update, core_api):
        context.return_value.config = {
            "namespace": "ns1",
            "node": {"existingSecret": "node-secret"},
        }
        result = CliRunner().invoke(
            cli_node_set_api_key, ["--name", "mynode", "--api-key", "new-key"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        update.assert_called_once_with(
            core_api.return_value, "node-secret", "ns1", {"V6_API_KEY": "new-key"}
        )

    @patch("vantage6.cli.context.node.get_core_api_with_ssl_handling")
    @patch("vantage6.cli.context.node.read_kubernetes_secret_value")
    def test_identifier_read_from_secret(self, read_value, _core_api):
        read_value.return_value = "some-api-key"
        ctx = NodeContext.__new__(NodeContext)
        ctx.in_container = False
        ctx.config = {"namespace": "ns1", "node": {"existingSecret": "node-secret"}}
        with_key = NodeContext.__new__(NodeContext)
        with_key.in_container = False
        with_key.config = {"node": {"apiKey": "some-api-key"}}

        self.assertEqual(ctx.identifier, with_key.identifier)
        read_value.assert_called_once_with(
            _core_api.return_value, "node-secret", "ns1", "V6_API_KEY"
        )


class TestSecretReferences(unittest.TestCase):
    CONFIG: ClassVar[dict] = {
        "hubGateway": {"tls": {"existingSecrets": {"hq": "tls-secret"}}},
        "auth": {
            "keycloak": {"auth": {"adminUserSecret": "kc-admin"}},
            "database": {"existingSecret": "auth-db"},
        },
        "hq": {"hq": {"existingSecret": "hq-secret"}},
        "store": {"store": {"existingSecret": ""}},
    }

    def test_referenced_secret_names(self):
        self.assertEqual(
            sorted(referenced_secret_names(self.CONFIG)),
            ["auth-db", "hq-secret", "kc-admin"],
        )

    @patch("vantage6.cli.common.utils.kubernetes_secret_exists")
    @patch("vantage6.cli.common.utils.get_core_api_with_ssl_handling")
    def test_missing_secret_exits(self, _core_api, exists):
        exists.side_effect = lambda _api, name, _namespace: name != "hq-secret"
        with self.assertRaises(SystemExit):
            ensure_referenced_secrets_exist(
                self.CONFIG, KubernetesConfig(namespace="ns1")
            )
        exists.side_effect = None
        exists.return_value = True
        ensure_referenced_secrets_exist(self.CONFIG, KubernetesConfig(namespace="ns1"))

    @patch("vantage6.cli.common.utils.delete_kubernetes_secret")
    @patch("vantage6.cli.common.utils.create_kubernetes_secret")
    @patch("vantage6.cli.common.utils.kubernetes_secret_exists", return_value=False)
    @patch("vantage6.cli.common.utils.get_core_api_with_ssl_handling")
    def test_store_credentials_rolls_back_on_failure(
        self, _core_api, _exists, create, delete
    ):
        create.side_effect = [None, ApiException(status=500)]
        with self.assertRaises(SystemExit):
            store_credentials_in_kubernetes_secrets(
                KubernetesConfig(namespace="ns1"), {"first": {}, "second": {}}
            )
        delete.assert_called_once_with(_core_api.return_value, "first", "ns1")


class TestRemoveSecrets(unittest.TestCase):
    CONFIG: ClassVar[dict] = {"namespace": "ns1", "node": {"existingSecret": "s1"}}

    @patch("vantage6.cli.common.remove.q")
    @patch("vantage6.cli.common.remove.delete_kubernetes_secret")
    @patch("vantage6.cli.common.remove.get_core_api_with_ssl_handling")
    @patch("vantage6.cli.common.remove.select_k8s_config")
    def test_force_deletes_without_asking(self, k8s, core_api, delete, q):
        _remove_referenced_secrets(self.CONFIG, force=True)
        q.confirm.assert_not_called()
        delete.assert_called_once_with(core_api.return_value, "s1", "ns1")

    @patch("vantage6.cli.common.remove.q")
    @patch("vantage6.cli.common.remove.delete_kubernetes_secret")
    def test_secrets_kept_unless_confirmed(self, delete, q):
        q.confirm.return_value.unsafe_ask.return_value = False
        _remove_referenced_secrets(self.CONFIG, force=False)
        delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
