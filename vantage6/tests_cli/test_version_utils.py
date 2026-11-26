import unittest
from unittest.mock import patch

from vantage6.cli.common.start import helm_install
from vantage6.cli.globals import ChartName
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.utils import (
    normalize_image_tag,
    to_helm_chart_version,
    to_image_version,
)


class VersionFormatTest(unittest.TestCase):
    def test_to_helm_chart_version(self):
        cases = {
            "5.0.4rc1": "5.0.4-rc1",
            "5.0.4-rc1": "5.0.4-rc1",
            "5.0.0a2": "5.0.0-a2",
            "5.0.0b3.post1": "5.0.0-b3.post1",
            "5.0.4": "5.0.4",
        }
        for version, expected in cases.items():
            with self.subTest(version=version):
                self.assertEqual(to_helm_chart_version(version), expected)

    def test_to_image_version(self):
        cases = {
            "5.0.4-rc1": "5.0.4rc1",
            "5.0.4rc1": "5.0.4rc1",
            "5.0.0-a2": "5.0.0a2",
            "5.0.0-b3.post1": "5.0.0b3.post1",
            "5.0.4": "5.0.4",
            "latest": "latest",
        }
        for version, expected in cases.items():
            with self.subTest(version=version):
                self.assertEqual(to_image_version(version), expected)

    def test_normalize_image_tag(self):
        cases = {
            None: None,
            "": "",
            "ghcr.io/vantage6/infrastructure/hq:5.0.4-rc1": (
                "ghcr.io/vantage6/infrastructure/hq:5.0.4rc1"
            ),
            "ghcr.io/vantage6/infrastructure/hq:5.0.4rc1": (
                "ghcr.io/vantage6/infrastructure/hq:5.0.4rc1"
            ),
            "localhost:5000/hq:5.0.4-rc1": "localhost:5000/hq:5.0.4rc1",
            "localhost:5000/hq": "localhost:5000/hq",
            "hq": "hq",
            "hq:latest": "hq:latest",
            "hq@sha256:abc": "hq@sha256:abc",
        }
        for image, expected in cases.items():
            with self.subTest(image=image):
                self.assertEqual(normalize_image_tag(image), expected)


class HelmInstallChartVersionTest(unittest.TestCase):
    @patch("vantage6.cli.common.start.subprocess.run")
    def test_chart_version_is_converted_to_helm_format(self, run):
        helm_install(
            release_name="release",
            chart_name=ChartName.HUB,
            k8s_config=KubernetesConfig(context="ctx", namespace="ns"),
            chart_version="5.0.4rc1",
        )

        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--version") + 1], "5.0.4-rc1")
