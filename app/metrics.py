"""Prometheus metrics for Barua Pepe."""

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
except ModuleNotFoundError as error:
    if error.name != "prometheus_client":
        raise

    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _NoOpMetric:
        """Metric-compatible fallback used when Prometheus is not installed."""

        def __init__(self, *_args, **_kwargs):
            """Accept the same construction arguments as Prometheus metrics."""

        def labels(self, *_args, **_kwargs):
            """Return self to preserve the Prometheus label API."""
            return self

        def inc(self, _amount=1):
            """Accept counter updates without recording them."""
            return None

        def observe(self, _amount):
            """Accept observations without recording them."""
            return None

        def set(self, _value):
            """Accept gauge updates without recording them."""
            return None

        def collect(self):
            """Return no samples."""
            return []

    class Counter(_NoOpMetric):
        """No-op fallback counter."""

    class Gauge(_NoOpMetric):
        """No-op fallback gauge."""

    class Histogram(_NoOpMetric):
        """No-op fallback histogram."""

    def generate_latest():
        """Return an empty Prometheus payload."""
        return b""


__all__ = [
    "CONTENT_TYPE_LATEST",
    "email_error_tasks",
    "email_send_attempts",
    "email_send_failures",
    "event_processing_latency_ms",
    "generate_latest",
    "task_latency_seconds",
    "task_pending_count",
    "task_queue_depth",
]


# Counters for email sending flows
email_send_attempts = Counter(
    "barua_email_send_attempts_total",
    "Total email send attempts",
)
email_send_failures = Counter(
    "barua_email_send_failures_total",
    "Total failed email sends",
)
email_error_tasks = Counter(
    "barua_email_error_tasks_total",
    "Total messages routed to error queue",
)

# Histograms for task performance
task_latency_seconds = Histogram(
    "barua_task_latency_seconds",
    "Task execution duration in seconds reported by Celery events",
    labelnames=["task_name", "state"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),  # typical email send times
)

event_processing_latency_ms = Histogram(
    "barua_event_processing_latency_ms",
    "Celery event processing latency in milliseconds",
    buckets=(1.0, 5.0, 10.0, 25.0, 50.0, 100.0),
)

# Gauge for task ids observed in the event stream
task_pending_count = Gauge(
    "barua_task_pending_count",
    "Number of task ids tracked from sent or started events through completion",
)

task_queue_depth = Gauge(
    "barua_task_queue_depth",
    "Number of ready messages in each configured Celery broker queue",
    labelnames=["queue_name"],
)
