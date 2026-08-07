"""Prometheus metrics for Barua Pepe"""

try:
    from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
except Exception:  # pragma: no cover - optional in environments without prometheus_client
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass


# Counters for email sending flows
email_send_attempts = Counter("barua_email_send_attempts_total", "Total email send attempts",)
email_send_failures = Counter("barua_email_send_failures_total", "Total failed email sends")
email_error_tasks = Counter("barua_email_error_tasks_total", "Total messages routed to error queue")
