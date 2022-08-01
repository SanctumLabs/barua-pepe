"""
Error Tasks
"""
import os
from app.worker.celery_app import celery_app
from app.domain.entities import EmailRequest
from app.logger import log

broker_host = os.environ.get("BROKER_HOST")
broker_port = os.environ.get("BROKER_PORT")
broker_username = os.environ.get("BROKER_USER")
broker_password = os.environ.get("BROKER_PASSWORD")


@celery_app.task(
    bind=True,
    default_retry_delay=30,
    max_retries=3,
    name="mail_error_task",
    acks_late=True,
)
@log.catch
# pylint: disable=too-many-arguments
def mail_error_task(
    # pylint: disable=unused-argument
    self,
    data: EmailRequest,
):
    """
    Mail Error Task. This handles tasks that have failed to deliver messages
    """
    log.info(f"Received Data={data}")


@celery_app.task(
    bind=True, default_retry_delay=30, max_retries=2, name="mail_error_callback_task"
)
@log.catch
# pylint: disable=unused-argument
def mail_error_callback_task(self):
    """
    This handles even callbacks for emails as received from SMTP or email provider. In the event there was a failure in
    sending out an email address
    """
