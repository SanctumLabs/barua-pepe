"""Prometheus metrics for Barua Pepe."""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

__all__ = [
    "CONTENT_TYPE_LATEST",
    "email_error_tasks",
    "email_send_attempts",
    "email_send_failures",
    "event_processing_latency_ms",
    "generate_latest",
    "task_latency_seconds",
    "task_pending_count",
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
