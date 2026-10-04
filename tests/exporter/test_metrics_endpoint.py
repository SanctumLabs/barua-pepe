"""Tests for the Prometheus metrics endpoint."""

import builtins
import importlib.util
from pathlib import Path

from app.api.monitoring.routes import metrics
from app.metrics import CONTENT_TYPE_LATEST


def test_metrics_module_has_noop_fallback_without_prometheus(monkeypatch):
    original_import = builtins.__import__

    def import_without_prometheus(name, *args, **kwargs):
        if name == "prometheus_client":
            raise ModuleNotFoundError("prometheus_client is unavailable", name=name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_prometheus)
    module_path = Path(__file__).parents[2] / "app" / "metrics.py"
    spec = importlib.util.spec_from_file_location(
        "metrics_without_prometheus", module_path
    )
    fallback_metrics = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(fallback_metrics)
    fallback_metrics.email_send_attempts.inc()
    fallback_metrics.task_latency_seconds.labels(
        task_name="task", state="success"
    ).observe(0.5)
    fallback_metrics.task_queue_depth.labels(queue_name="mail").set(2)

    assert fallback_metrics.generate_latest() == b""
    assert fallback_metrics.task_latency_seconds.collect() == []


def test_metrics_endpoint_returns_prometheus_payload():
    response = metrics()

    assert response.media_type == CONTENT_TYPE_LATEST
    assert b"barua_task_latency_seconds" in response.body
