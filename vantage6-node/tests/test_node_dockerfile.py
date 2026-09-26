import re
from pathlib import Path
from unittest import TestCase

DOCKERFILE = Path(__file__).parents[2] / "docker" / "node.Dockerfile"
MAKEFILE = Path(__file__).parents[2] / "Makefile"


class TestNodeDockerfile(TestCase):
    """node.Dockerfile must stay leaner than the old combined image: no CLI, no pandas."""

    def setUp(self):
        self.content = DOCKERFILE.read_text()

    def test_does_not_copy_the_cli_package(self):
        # Must check exact path segments, not substring match (vantage6-common
        # and vantage6-node also start with "vantage6").
        for line in self.content.splitlines():
            if line.strip().startswith("COPY"):
                sources = line.split()[1:-1]
                self.assertNotIn(
                    "vantage6",
                    sources,
                    "node.Dockerfile must not COPY the vantage6 CLI package",
                )

    def test_does_not_copy_algorithm_tools(self):
        self.assertNotIn(
            "vantage6-algorithm-tools",
            self.content,
            "node.Dockerfile must not depend on vantage6-algorithm-tools "
            "(and therefore pandas) -- see lite-01",
        )

    def test_copies_common_and_node_packages(self):
        self.assertIn("COPY vantage6-common", self.content)
        self.assertIn("COPY vantage6-node", self.content)

    def test_uses_a_multi_stage_builder(self):
        # Two FROM lines + --from=builder is the multi-stage signal.
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

    def test_copies_the_readme(self):
        # setup.py reads ../README.md; pip install -e . fails without this COPY.
        self.assertIn("COPY README.md", self.content)

    def test_builder_and_final_stage_use_the_same_base_image(self):
        # Pinned separately per FROM line rather than via a shared ARG.
        images = re.findall(r"^FROM (\S+)", self.content, re.MULTILINE)
        self.assertEqual(len(images), 2)
        self.assertEqual(
            images[0],
            images[1],
            "builder and final stage must pin the exact same base image",
        )


class TestMakefileBuildsThisDockerfile(TestCase):
    """Guards against `make image` silently building the old combined Dockerfile again."""

    def setUp(self):
        self.content = MAKEFILE.read_text()

    def test_node_image_target_builds_the_new_dockerfile(self):
        self.assertIn("./docker/node.Dockerfile", self.content)

    def test_old_combined_dockerfile_is_no_longer_referenced(self):
        self.assertNotIn("node-and-server.Dockerfile", self.content)
