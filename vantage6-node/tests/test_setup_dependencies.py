import ast
from pathlib import Path
from unittest import TestCase


def _install_requires(setup_py: Path) -> list[str]:
    """Extract the `install_requires` list from a setup.py without
    executing it (executing it would actually invoke setuptools)."""
    tree = ast.parse(setup_py.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "setup":
            for kw in node.keywords:
                if kw.arg == "install_requires":
                    names = []
                    for elt in kw.value.elts:
                        # plain string literals, e.g. "flask==3.1.3"
                        if isinstance(elt, ast.Constant):
                            names.append(elt.value)
                        # f-strings, e.g. f"vantage6-common == {version}"
                        elif isinstance(elt, ast.JoinedStr):
                            names.append(
                                "".join(
                                    v.value
                                    for v in elt.values
                                    if isinstance(v, ast.Constant)
                                )
                            )
                    return names
    raise AssertionError(f"Could not find install_requires in {setup_py}")


class TestNodeSetupDependencies(TestCase):
    """flask and websocket-client are real runtime deps, not conveniences --
    both were previously masked by the CLI package's dependency tree."""

    def setUp(self):
        self.install_requires = _install_requires(
            Path(__file__).parents[1] / "setup.py"
        )

    def test_flask_is_a_hard_dependency(self):
        self.assertTrue(
            any(dep.startswith("flask==") for dep in self.install_requires),
            "flask must stay in install_requires: proxy_server.py imports it "
            "unconditionally at module level",
        )

    def test_websocket_client_is_a_hard_dependency(self):
        self.assertTrue(
            any(dep.startswith("websocket-client==") for dep in self.install_requires),
            "websocket-client must stay in install_requires: without it, the "
            "node silently downgrades to HTTP long-polling instead of using "
            "a websocket connection, with no error raised anywhere",
        )

    def test_cli_package_is_not_a_dependency(self):
        # vantage6-node must not need the CLI package to run.
        self.assertFalse(
            any(dep.startswith("vantage6 ==") for dep in self.install_requires),
            "vantage6-node must not depend on the vantage6 CLI package",
        )
