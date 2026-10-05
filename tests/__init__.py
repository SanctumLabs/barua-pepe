import os
import unittest
from httpx import ASGITransport, AsyncClient
from app.config import Config, get_config
from app import app
from app.services.auth.auth_service import get_current_auth


class BaseTestCase(unittest.TestCase):
    """
    Base test case for application
    """
    os.environ.update(SENTRY_ENABLED="False", RESULT_BACKEND="rpc")

    def setUp(self):
        app.dependency_overrides[get_config] = self._get_settings_override
        app.dependency_overrides[get_current_auth] = lambda: None
        self.async_client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        )

    def setup_method(self, method):
        self.setUp()

    def tearDown(self):
        pass

    def teardown_method(self, method):
        self.tearDown()

    @staticmethod
    def _get_settings_override():
        return Config(environment="test", sentry_debug_enabled=False, sentry_enabled=False, sentry_dsn="",
                      mail_smtp_enabled=False)

    def assert_status(self, status_code: int, actual: int):
        self.assertEqual(status_code, actual)


if __name__ == "__main__":
    unittest.main()
