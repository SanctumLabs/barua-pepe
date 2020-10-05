from app import celery_app
from app.logger import log
from app.constants import EMAIL_ERROR_EXCHANGE, EMAIL_ERROR_ROUTING_KEY, EMAIL_ERROR_QUEUE_NAME
from .exceptions import TaskException
import os

broker_host = os.environ.get("BROKER_HOST")
broker_port = os.environ.get("BROKER_PORT")
broker_username = os.environ.get("BROKER_USER")
broker_password = os.environ.get("BROKER_PASSWORD")

@celery_app.task(bind=True, default_retry_delay=30, max_retries=3, name="mail_error_task")
@log.catch
def mail_error_task(self, from_, to, cc, subject, bcc, message, attachments):
    log.info(f"Received from_={from_}, to:{to}, cc:{cc}, subject:{subject}, bcc:{bcc}, message:{message}, attachments:{attachments}")


@celery_app.task(bind=True, default_retry_delay=30, max_retries=2, name="mail_error_callback_task")
@log.catch
def mail_error_callback_task(self):
    """
    This handles even callbacks for emails as received from SMTP or email provider. In the event there was a failure in sending out an email
    address
    """
    pass
