from typing import Dict, List
from app.worker.celery_app import celery_app
from app.logger import log
import os

broker_host = os.environ.get("BROKER_HOST")
broker_port = os.environ.get("BROKER_PORT")
broker_username = os.environ.get("BROKER_USER")
broker_password = os.environ.get("BROKER_PASSWORD")


@celery_app.task(bind=True, default_retry_delay=30, max_retries=3, name="mail_error_task")
@log.catch
def mail_error_task(self, sender: Dict[str, str], recipients: List[Dict[str, str]],
                    subject: str, message: str, cc: List[Dict[str, str]] | None = None,
                    bcc: List[Dict[str, str]] | None = None, attachments: List[Dict[str, str]] | None = None):
    log.info(
        f"Received from_={sender}, to:{recipients}, cc:{cc}, subject:{subject}, bcc:{bcc}, message:{message}, "
        f"attachments:{attachments}")


@celery_app.task(bind=True, default_retry_delay=30, max_retries=2, name="mail_error_callback_task")
@log.catch
def mail_error_callback_task(self):
    """
    This handles even callbacks for emails as received from SMTP or email provider. In the event there was a failure in sending out an email
    address
    """
    pass
