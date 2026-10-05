"""
Mail sending tasks can be found here
"""

from typing import Any

from pydantic import ValidationError

from app.worker.celery_app import celery_app
from app.logger import log
from app.metrics import email_send_attempts, email_send_failures
from app.services.mail import send_plain_mail
from app.services.mail.exceptions import DeliveryOutcomeUnknownException
from app.domain.entities import EmailRequest
from .mail_error_task import mail_error_task


@celery_app.task(
    bind=True,
    default_retry_delay=30,
    max_retries=3,
    name="mail_sending_task",
    acks_late=True,
)
@log.catch(reraise=True)
def mail_sending_task(self, data: dict[str, Any], request_id: str | None = None):
    """
    Worker task that handles sending email messages in the background
    :param data: dict payload for the email
    :param request_id: optional request id propagated from the HTTP request
    """
    # bind a logger with context so structured logs include request_id and task id
    bound_log = log.bind(
        request_id=request_id, celery_task_id=getattr(self.request, "id", None)
    )
    try:
        email_request = EmailRequest.from_task_payload(data)
    except ValidationError as exc:
        bound_log.error(f"Invalid mail payload: {exc}")
        email_send_failures.inc()
        mail_error_task.apply_async(kwargs={"data": data, "request_id": request_id})
        raise
    try:
        bound_log.info("Processing mail_sending_task")
        email_send_attempts.inc()

        result = send_plain_mail(email_request)

        return result
    except DeliveryOutcomeUnknownException as exc:
        bound_log.error(
            f"Email delivery outcome is unknown; not retrying to avoid duplicate delivery: {exc}"
        )
        email_send_failures.inc()
        mail_error_task.apply_async(kwargs={"data": data, "request_id": request_id})
        raise
    # pylint: disable=broad-except
    except Exception as exc:
        bound_log.error(
            f"Error sending email with error {exc}. Attempt {self.request.retries}/{self.max_retries} ..."
        )

        email_send_failures.inc()

        if self.request.retries == self.max_retries:
            bound_log.warning("Maximum attempts reached, pushing to dlt queue...")
            mail_error_task.apply_async(kwargs={"data": data, "request_id": request_id})

        # exponential backoff: increase countdown (simple multiplier)
        countdown = 30 * (2**self.request.retries)
        raise self.retry(countdown=countdown, exc=exc)
