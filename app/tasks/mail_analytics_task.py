"""
Mail Analytics tasks can be found here
"""
from typing import Any

from app.worker.celery_app import celery_app
from app.logger import log
from app.services.mail import send_plain_mail
from app.domain.entities import EmailRequest


@celery_app.task(
    bind=True,
    default_retry_delay=30,
    max_retries=3,
    name="mail_analytics_task",
    acks_late=True,
)
@log.catch(reraise=True)
def mail_analytics_task(self, data: dict[str, Any]):
    """
    Task that handles analytics for email messages in the background. Whether there was a failed delivery, it's tracked
    here.
    """

    email_request = EmailRequest.from_task_payload(data)
    try:
        return send_plain_mail(email_request)
    # pylint: disable=broad-except
    except Exception as exc:
        log.error(
            f"[AnalyticsTask]: Error sending email with error {exc}. Attempt {self.request.retries}/{self.max_retries}"
        )
        raise self.retry(countdown=30 * 2, exc=exc, max_retries=3)
