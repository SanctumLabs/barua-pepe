from typing import Dict, List
from app.worker.celery_app import celery_app
from app.logger import log
from app.services.mail import send_plain_mail
from .mail_error_task import mail_error_task
from .exceptions import TaskException


@celery_app.task(
    bind=True, default_retry_delay=30, max_retries=3, name="mail_sending_task"
)
@log.catch
def mail_sending_task(
    self,
    sender: Dict[str, str],
    recipients: List[Dict[str, str]],
    subject: str,
    message: str,
    cc: List[Dict[str, str]] | None = None,
    bcc: List[Dict[str, str]] | None = None,
    attachments: List[Dict[str, str]] | None = None,
):
    data = dict(
        sender=sender,
        recipients=recipients,
        cc=cc,
        bcc=bcc,
        subject=subject,
        message=message,
        attachments=attachments,
    )

    try:
        result = send_plain_mail(**data)
        if not result:
            raise TaskException("Mail sending task failed")
        return result
    except Exception as exc:
        log.error(
            f"Error sending email with error {exc}. Attempt {self.request.retries}/{self.max_retries} ..."
        )

        if self.request.retries == self.max_retries:
            log.warning(f"Maximum attempts reached, pushing to error queue...")
            mail_error_task.apply_async(kwargs=data)

        raise self.retry(countdown=30 * 2, exc=exc, max_retries=3)
