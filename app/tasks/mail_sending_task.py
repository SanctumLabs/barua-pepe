"""
Mail sending tasks can be found here
"""
from app.worker.celery_app import celery_app
from app.logger import log
from app.services.mail import send_plain_mail
from app.domain.entities import EmailRequest
from .mail_error_task import mail_error_task


@celery_app.task(
    bind=True,
    default_retry_delay=30,
    max_retries=3,
    name="mail_sending_task",
    acks_late=True,
)
@log.catch
def mail_sending_task(self, data: EmailRequest):
    """
    Worker task that handles sending email messages in the background
    """
    try:
        return send_plain_mail(data)
    # pylint: disable=broad-except
    except Exception as exc:
        log.error(
            f"Error sending email with error {exc}. Attempt {self.request.retries}/{self.max_retries} ..."
        )

        if self.request.retries == self.max_retries:
            log.warning("Maximum attempts reached, pushing to dlt queue...")
            mail_error_task.apply_async(kwargs=dict(data=data.dict()))

        raise self.retry(countdown=30 * 2, exc=exc, max_retries=3)
