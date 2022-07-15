import os
import unittest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from app import app, get_config
from app.config import Config


class BaseTestCase(unittest.TestCase):
    """
    Base test case for application
    """
    os.environ.update(SENTRY_ENABLED="False", RESULT_BACKEND="rpc")

    def setUp(self):
        self.test_client = TestClient(app=app)

        app.dependency_overrides[get_config] = self._get_settings_override()

        self.async_client = AsyncClient(app=self.test_client, base_url="http://test")

    def tearDown(self):
        pass

    @staticmethod
    def _get_settings_override():
        return Config(environment="test", sentry_enabled=False, sentry_dsn="")

    def assert_status(self, status_code: int, actual: int):
        self.assertEqual(status_code, actual)


if __name__ == "__main__":
    unittest.main()
