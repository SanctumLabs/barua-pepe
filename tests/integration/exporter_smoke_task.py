"""A deterministic Celery task used by the exporter integration smoke test."""

from app.worker.celery_app import celery_app


@celery_app.task(name="exporter_smoke_task", ignore_result=True)
def exporter_smoke_task():
    """Return successfully without contacting an external mail provider."""
    return "ok"
