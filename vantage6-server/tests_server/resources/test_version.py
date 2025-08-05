import json
import logging

from vantage6.common import logger_name

from vantage6.server import __version__

from .test_resource_base import TestResourceBase

logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResourcesVersion(TestResourceBase):
    def test_version(self):
        rv = self.app.get("/api/version")
        r = json.loads(rv.data)
        self.assertIn("version", r)
        self.assertEqual(r["version"], __version__)
