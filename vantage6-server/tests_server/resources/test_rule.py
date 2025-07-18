import logging

from vantage6.common import logger_name
from .test_resource_base import TestResourceBase


logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):
    def test_view_rules(self):
        headers = self.login_as_root()
        result = self.app.get("/api/rule", headers=headers)
        self.assertEqual(result.status_code, 200)
