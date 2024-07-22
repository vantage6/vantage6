from unittest import TestCase

from vantage6.common.docker.addons import parse_image_name
from docker.errors import InvalidRepository


# These tests are adapted from [1]. We do this because parse_image_name uses
# internal docker-py functions, which may change without notice in future
# versions.
# [1]: https://github.com/docker/docker-py/blob/9ad4bddc9ee23f3646f256280a21ef86274e39bc/tests/unit/auth_test.py#L27s
class TestParseImageName(TestCase):
    def test_parse_image_name_hub_library_image(self):
        self.assertEqual(parse_image_name("image"), ("docker.io", "image", "latest"))

    def test_parse_image_name_dotted_hub_library_image(self):
        self.assertEqual(
            parse_image_name("image.valid"), ("docker.io", "image.valid", "latest")
        )

    def test_parse_image_name_hub_image_with_user(self):
        self.assertEqual(
            parse_image_name("username/image"),
            ("docker.io", "username/image", "latest"),
        )

    def test_parse_image_name_explicit_hub_library_image(self):
        self.assertEqual(
            parse_image_name("docker.io/image"), ("docker.io", "image", "latest")
        )

    def test_parse_image_name_explicit_legacy_hub_library_image(self):
        self.assertEqual(
            parse_image_name("index.docker.io/image"), ("docker.io", "image", "latest")
        )

    def test_parse_image_name_private_registry(self):
        self.assertEqual(
            parse_image_name("my.registry.net/image"),
            ("my.registry.net", "image", "latest"),
        )

    def test_parse_image_name_private_registry_with_port(self):
        self.assertEqual(
            parse_image_name("my.registry.net:5000/image"),
            ("my.registry.net:5000", "image", "latest"),
        )

    def test_parse_image_name_private_registry_with_user(self):
        self.assertEqual(
            parse_image_name("my.registry.net/username/image"),
            ("my.registry.net", "username/image", "latest"),
        )

    def test_parse_image_name_no_dots_but_port(self):
        self.assertEqual(
            parse_image_name("hostname:5000/image"),
            ("hostname:5000", "image", "latest"),
        )

    def test_parse_image_name_no_dots_but_port_and_username(self):
        self.assertEqual(
            parse_image_name("hostname:5000/username/image"),
            ("hostname:5000", "username/image", "latest"),
        )

    def test_parse_image_name_localhost(self):
        self.assertEqual(
            parse_image_name("localhost/image"), ("localhost", "image", "latest")
        )

    def test_parse_image_name_localhost_with_username(self):
        self.assertEqual(
            parse_image_name("localhost/username/image"),
            ("localhost", "username/image", "latest"),
        )

    def test_parse_image_name_invalid(self):
        with self.assertRaises(InvalidRepository):
            parse_image_name("-gecko.com/image")

    def test_parse_image_different_tag(self):
        self.assertEqual(parse_image_name("image:tag"), ("docker.io", "image", "tag"))

    def test_parse_image_different_tag_and_registry(self):
        self.assertEqual(
            parse_image_name("my.registry.net:5000/image:tag"),
            ("my.registry.net:5000", "image", "tag"),
        )

    def test_parse_image_different_tag_and_registry_and_nested(self):
        self.assertEqual(
            parse_image_name("my.registry.net:5000/nested/image:tag"),
            ("my.registry.net:5000", "nested/image", "tag"),
        )

    def test_parse_image_different_tag_and_registry_and_nested_double(self):
        self.assertEqual(
            parse_image_name("my.registry.net:5000/nested/double/image:tag2"),
            ("my.registry.net:5000", "nested/double/image", "tag2"),
        )

    def test_parse_image_different_tag_and_registry_and_nested_triple(self):
        self.assertEqual(
            parse_image_name("my.registry.net:5000/nested/double/triple/image:Three"),
            ("my.registry.net:5000", "nested/double/triple/image", "Three"),
        )

    def test_parse_image_different_tag_and_registry_and_nested_triple_with_port(self):
        self.assertEqual(
            parse_image_name("example.com/nested/double/triple/image:Three"),
            ("example.com", "nested/double/triple/image", "Three"),
        )

    def test_parse_image_name_harbor2_average(self):
        self.assertEqual(
            parse_image_name("harbor2.vantage6.ai/demo/average"),
            ("harbor2.vantage6.ai", "demo/average", "latest"),
        )

    def test_parse_image_name_harbor2_average_tag_latest(self):
        self.assertEqual(
            parse_image_name("harbor2.vantage6.ai/demo/average:latest"),
            ("harbor2.vantage6.ai", "demo/average", "latest"),
        )

    def test_parse_image_name_harbor2_average_tag_4(self):
        self.assertEqual(
            parse_image_name("harbor2.vantage6.ai/demo/average:4"),
            ("harbor2.vantage6.ai", "demo/average", "4"),
        )

    def test_parse_image_name_with_sha(self):
        self.assertEqual(
            parse_image_name("harbor2.vantage6.ai/demo/average@sha256:1234"),
            ("harbor2.vantage6.ai", "demo/average", "sha256:1234"),
        )

    def test_parse_image_name_with_sha_and_tag(self):
        self.assertEqual(
            parse_image_name(
                "harbor2.vantage6.ai/infrastructure/node:4.5@sha256:1234567890abcdef"
                "1234567890abcdef1234567890abcdef1234567890abcdef"
            ),
            (
                "harbor2.vantage6.ai",
                "infrastructure/node",
                "4.5",
            ),
        )
