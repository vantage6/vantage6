import time
from http import HTTPStatus
from unittest.mock import patch

import jwt

from vantage6.common.globals import DEFAULT_CONTAINER_TOKEN_EXPIRES_HOURS

from .test_resource_base import TestResourceBase


class TestContainerToken(TestResourceBase):
    def _decode_container_token(self, headers: dict) -> dict:
        token = headers["Authorization"].removeprefix("Bearer ")
        return jwt.decode(
            token,
            self.server.app.config["jwt_secret_key"],
            algorithms=["HS256"],
            options={"verify_sub": False},
        )

    def test_container_token_expires_after_default_period(self):
        claims = self._decode_container_token(self.login_container())

        expected_exp = time.time() + DEFAULT_CONTAINER_TOKEN_EXPIRES_HOURS * 3600
        self.assertAlmostEqual(claims["exp"], expected_exp, delta=60)

    def test_container_token_expiry_is_configurable(self):
        with patch.dict(
            self.server.ctx.config, {"jwt_container_token_expires_hours": 1}
        ):
            claims = self._decode_container_token(self.login_container())

        self.assertAlmostEqual(claims["exp"], time.time() + 3600, delta=60)

    def test_expired_container_token_is_rejected(self):
        node = self.create_node()
        with patch.dict(
            self.server.ctx.config, {"jwt_container_token_expires_hours": -1}
        ):
            headers = self.login_container(node=node)

        result = self.app.get(
            f"/api/organization/{node.organization.id}", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
