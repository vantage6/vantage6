import ast
from pathlib import Path
from unittest import TestCase

DOCKERFILE = Path(__file__).parents[2] / "docker" / "server.Dockerfile"
SETUP_PY = Path(__file__).parents[1] / "setup.py"
MAKEFILE = Path(__file__).parents[2] / "Makefile"


def _extras_require(setup_py: Path) -> dict:
    """Extract the `extras_require` dict from setup.py without executing
    it (executing it would actually invoke setuptools)."""
    tree = ast.parse(setup_py.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "setup":
            for kw in node.keywords:
                if kw.arg == "extras_require":
                    result = {}
                    for key_node, val_node in zip(kw.value.keys, kw.value.values):
                        result[key_node.value] = [
                            elt.value
                            for elt in val_node.elts
                            if isinstance(elt, ast.Constant)
                        ]
                    return result
    raise AssertionError(f"Could not find extras_require in {setup_py}")


class TestServerDockerfile(TestCase):
    """server.Dockerfile must stay leaner than the old combined image: no CLI,
    postgres only via an extra."""

    def setUp(self):
        self.content = DOCKERFILE.read_text()

    def test_does_not_copy_the_cli_package(self):
        for line in self.content.splitlines():
            if line.strip().startswith("COPY"):
                sources = line.split()[1:-1]
                self.assertNotIn(
                    "vantage6",
                    sources,
                    "server.Dockerfile must not COPY the vantage6 CLI package",
                )

    def test_copies_the_expected_packages(self):
        self.assertIn("COPY vantage6-common", self.content)
        self.assertIn("COPY vantage6-backend-common", self.content)
        self.assertIn("COPY vantage6-server", self.content)

    def test_installs_the_postgres_extra(self):
        self.assertIn('vantage6-server[postgres]"', self.content)

    def test_installs_uwsgi(self):
        self.assertIn("uwsgi==2.0.31", self.content)

    def test_uses_a_multi_stage_builder(self):
        self.assertEqual(self.content.count("FROM "), 2)
        self.assertIn("COPY --from=builder", self.content)

    def test_final_stage_does_not_install_build_tooling(self):
        # Build tooling must not leak into the final stage.
        _builder_stage, final_stage = self.content.split("FROM ")[1:]
        self.assertNotIn("apt-get install", final_stage)

    def test_final_stage_declares_a_version_label(self):
        # LABELs in the builder stage don't carry into the final image.
        _builder_stage, final_stage = self.content.split("FROM ")[1:]
        self.assertIn("ARG TAG=", final_stage)
        self.assertIn("LABEL version=${TAG}", final_stage)


class TestServerSetupPostgresExtra(TestCase):
    """The `postgres` extra must exist and declare psycopg2, or the Dockerfile
    installs the server with no database driver."""

    def setUp(self):
        self.extras = _extras_require(SETUP_PY)

    def test_postgres_extra_exists(self):
        self.assertIn("postgres", self.extras)

    def test_postgres_extra_declares_psycopg2(self):
        self.assertTrue(
            any(dep.startswith("psycopg2-binary==") for dep in self.extras["postgres"])
        )


class TestMakefileBuildsThisDockerfile(TestCase):
    """Guards against `make image` silently building the old combined Dockerfile again."""

    def setUp(self):
        self.content = MAKEFILE.read_text()

    def test_server_image_target_builds_the_new_dockerfile(self):
        self.assertIn("./docker/server.Dockerfile", self.content)

    def test_old_combined_dockerfile_is_no_longer_referenced(self):
        self.assertNotIn("node-and-server.Dockerfile", self.content)
