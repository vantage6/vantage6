import os
import unittest
from typing import ClassVar
from unittest.mock import patch

from vantage6.common.context import AppContext
from vantage6.common.globals import InstanceType


class OverrideContext(AppContext):
    CONFIG_ENV_OVERRIDES: ClassVar[dict[str, tuple[str, ...]]] = {
        "V6_TEST_URI": ("uri",),
        "V6_TEST_NESTED": ("section", "password"),
        "V6_TEST_JSON": ("registries",),
    }
    CONFIG_ENV_JSON: ClassVar[dict[str, type]] = {"V6_TEST_JSON": list}


def _context(config: dict) -> OverrideContext:
    ctx = OverrideContext.__new__(OverrideContext)
    ctx.config = config
    return ctx


class TestConfigEnvOverrides(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "V6_TEST_URI": "postgresql://u:p@db/x",
            "V6_TEST_NESTED": "secret",
            "V6_TEST_JSON": '[{"registry": "r.io", "password": "pw"}]',
        },
    )
    def test_overrides_applied(self):
        ctx = _context({"uri": "old", "section": {"host": "smtp"}})
        ctx._apply_config_env_overrides()
        self.assertEqual(ctx.config["uri"], "postgresql://u:p@db/x")
        self.assertEqual(ctx.config["section"], {"host": "smtp", "password": "secret"})
        self.assertEqual(
            ctx.config["registries"], [{"registry": "r.io", "password": "pw"}]
        )

    @patch.dict(os.environ, {"V6_TEST_NESTED": "secret"})
    def test_missing_parent_is_created(self):
        ctx = _context({"section": None})
        ctx._apply_config_env_overrides()
        self.assertEqual(ctx.config["section"], {"password": "secret"})

    @patch.dict(os.environ, {"V6_TEST_URI": ""}, clear=True)
    def test_unset_and_empty_are_ignored(self):
        ctx = _context({"uri": "old"})
        ctx._apply_config_env_overrides()
        self.assertEqual(ctx.config, {"uri": "old"})

    def test_invalid_json_is_rejected_without_value(self):
        for value, error in (
            ("not json SENTINEL", "valid JSON"),
            ('{"SENTINEL": 1}', "JSON list"),
        ):
            with (
                patch.dict(os.environ, {"V6_TEST_JSON": value}),
                self.assertRaises(ValueError) as cm,
            ):
                _context({})._apply_config_env_overrides()
            self.assertIn("V6_TEST_JSON", str(cm.exception))
            self.assertIn(error, str(cm.exception))
            self.assertNotIn("SENTINEL", str(cm.exception))
            self.assertIsNone(cm.exception.__cause__)

    def test_only_applied_in_container(self):
        for in_container in (True, False):
            ctx = OverrideContext.__new__(OverrideContext)
            with (
                patch.object(OverrideContext, "find_config_file"),
                patch.object(OverrideContext, "config_file"),
                patch.object(OverrideContext, "set_folders"),
                patch.object(OverrideContext, "setup_logging"),
                patch.object(OverrideContext, "print_log_header"),
                patch.object(
                    OverrideContext, "_apply_config_env_overrides"
                ) as apply_overrides,
            ):
                ctx.initialize(
                    InstanceType.NODE,
                    "test",
                    print_log_header=False,
                    in_container=in_container,
                )
            self.assertEqual(apply_overrides.called, in_container)
