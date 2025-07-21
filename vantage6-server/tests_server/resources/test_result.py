import logging

from vantage6.common import logger_name
from .test_resource_base import TestResourceBase


logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):

    def test_result_with_id(self):
        headers = self.login_as_root()
        run = self.create_run()
        result = self.app.get(f"/api/run/{run.id}", headers=headers)
        self.assertEqual(result.status_code, 200)

        result = self.app.get(f"/api/run/{run.id}?include=task", headers=headers)
        self.assertEqual(result.status_code, 200)
