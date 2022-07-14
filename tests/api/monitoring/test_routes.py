import unittest
from httpx import AsyncClient
import pytest
from tests import BaseTestCase


class MonitoringRoutesTestCase(BaseTestCase):

    @pytest.mark.anyio
    async def test_monitoring_route(self):
        async with AsyncClient(app=self.test_app, base_url="http://test") as ac:
            response = await ac.get("/healthz")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"message": "Healthy!"}, response.json())


if __name__ == '__main__':
    unittest.main()
