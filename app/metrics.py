"""Prometheus metrics for Barua Pepe"""

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
except Exception:  # pragma: no cover - optional in environments without prometheus_client
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

        def labels(self, **kwargs):
            return self

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

        def dec(self, *args, **kwargs):
            pass


# Counters for email sending flows
email_send_attempts = Counter(
    "barua_email_send_attempts_total",
    "Total email send attempts",
)
email_send_failures = Counter(
    "barua_email_send_failures_total",
    "Total failed email sends"
)
email_error_tasks = Counter(
    "barua_email_error_tasks_total",
    "Total messages routed to error queue"
)

# Histograms for task performance
task_latency_seconds = Histogram(
    "barua_task_latency_seconds",
    "Task execution latency in seconds (from sent to completed)",
    labelnames=["task_name", "state"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),  # typical email send times
)

event_processing_latency_ms = Histogram(
    "barua_event_processing_latency_ms",
    "Celery event processing latency in milliseconds",
    buckets=(1.0, 5.0, 10.0, 25.0, 50.0, 100.0),
)

# Gauge for queue depth
task_queue_depth = Gauge(
    "barua_task_queue_depth",
    "Current number of pending tasks in flight",
)
