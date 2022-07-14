import os
import unittest
from fastapi.testclient import TestClient
from app import app


class BaseTestCase(unittest.TestCase):
    """
    Base test case for application
    """
    os.environ.update(SENTRY_ENABLED="False", RESULT_BACKEND="rpc")

    def setUp(self):
        self.test_app = TestClient(app=app)

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
