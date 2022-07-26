import os
import unittest
from unittest import mock
from fastapi.testclient import TestClient
from httpx import AsyncClient
from app.config import Config, get_config
from app import app


class BaseTestCase(unittest.TestCase):
    """
    Base test case for application
    """
    os.environ.update(SENTRY_ENABLED="False", RESULT_BACKEND="rpc")

    def setUp(self):
        self.test_client = TestClient(app=app)

        app.dependency_overrides[get_config] = self._get_settings_override()

        self.async_client = AsyncClient(app=self.test_client, base_url="http://test")
        with mock.patch('app.services.mail.SmtpServer') as mock_smtp:
            mock_smtp.login = lambda x: print(x)
            mock_smtp.logout = lambda x: print(x)

    def tearDown(self):
        pass

    @staticmethod
    def _get_settings_override():
        return Config(environment="test", sentry_enabled=False, sentry_dsn="", mail_smtp_enabled=False)

    def assert_status(self, status_code: int, actual: int):
        self.assertEqual(status_code, actual)


if __name__ == "__main__":
    unittest.main()
