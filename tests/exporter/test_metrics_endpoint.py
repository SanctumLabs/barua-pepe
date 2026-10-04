"""Tests for the Prometheus metrics endpoint."""

from app.api.monitoring.routes import metrics
from app.metrics import CONTENT_TYPE_LATEST


def test_metrics_endpoint_returns_prometheus_payload():
    response = metrics()

    assert response.media_type == CONTENT_TYPE_LATEST
    assert b"barua_task_latency_seconds" in response.body
