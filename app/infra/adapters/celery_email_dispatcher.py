"""Celery adapter for asynchronous email dispatch."""

from app.domain.entities import EmailRequest
from app.tasks.mail_sending_task import mail_sending_task


# pylint: disable=too-few-public-methods
class CeleryEmailDispatcher:
    """Publishes validated email requests to the mail-sending task queue."""

    def dispatch(self, request: EmailRequest, request_id: str | None = None) -> None:
        """Publish an email request for asynchronous processing."""
        mail_sending_task.apply_async(
            kwargs={
                "data": request.to_task_payload(),
                "request_id": request_id,
            }
        )


celery_email_dispatcher = CeleryEmailDispatcher()
