import json
import unittest

from vantage6.algorithm.store import __version__

from ..base.unittest_base import TestResources


class TestAlgorithmResources(TestResources):
    def test_version(self):
        rv = self.app.get("/api/version")
        r = json.loads(rv.data)
        self.assertIn("version", r)
        self.assertEqual(r["version"], __version__)


if __name__ == "__main__":
    unittest.main()
