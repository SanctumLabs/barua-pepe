"""
Mail sending tasks can be found here
"""
from app.worker.celery_app import celery_app
from app.logger import log
from app.services.mail import send_plain_mail
from .mail_error_task import mail_error_task


@celery_app.task(
    bind=True,
    default_retry_delay=30,
    max_retries=3,
    name="mail_sending_task",
    acks_late=True,
)
@log.catch
def mail_sending_task(self, data: dict, request_id: str | None = None):
    """
    Worker task that handles sending email messages in the background
    :param data: dict payload for the email
    :param request_id: optional request id propagated from the HTTP request
    """
    # bind a logger with context so structured logs include request_id and task id
    bound_log = log.bind(request_id=request_id, celery_task_id=getattr(self.request, 'id', None))
    try:
        bound_log.info("Processing mail_sending_task")
        from app.metrics import email_send_attempts, email_send_failures

        # count attempt
        try:
            email_send_attempts.inc()
        except Exception:
            pass

        result = send_plain_mail(data)

        return result
    # pylint: disable=broad-except
    except Exception as exc:
        bound_log.error(
            f"Error sending email with error {exc}. Attempt {self.request.retries}/{self.max_retries} ..."
        )

        try:
            from app.metrics import email_send_failures

            email_send_failures.inc()
        except Exception:
            pass

        if self.request.retries == self.max_retries:
            bound_log.warning("Maximum attempts reached, pushing to dlt queue...")
            # ensure request_id is forwarded to the error queue
            mail_error_task.apply_async(kwargs=dict(data=data, request_id=request_id))

        # exponential backoff: increase countdown (simple multiplier)
        countdown = 30 * (2 ** self.request.retries)
        raise self.retry(countdown=countdown, exc=exc)
