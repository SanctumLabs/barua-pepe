from app import celery_app
from app.logger import log
from app.services.email import send_plain_mail
from app.constants import EMAIL_ERROR_EXCHANGE, EMAIL_ERROR_ROUTING_KEY
from .exceptions import TaskException
import pika
import os
import json

broker_host = os.environ.get("BROKER_HOST")


@celery_app.task(bind=True, default_retry_delay=30, max_retries=3, name="mail_sending_task")
@log.catch
def mail_sending_task(self, from_, to, cc, subject, bcc, message, attachments):
    try:
        result = send_plain_mail(
            from_=from_,
            to=to,
            cc=cc,
            subject=subject,
            bcc=bcc,
            message=message,
            attachments=attachments
        )

        if not result:
            raise TaskException("Mail sending task failed")
        return result
    except Exception as exc:
        log.error(f"Error sending email with error {exc}. Attempt {self.request.retries}/{self.max_retries} ...")

        if self.request.retries == self.max_retries:
            log.warning(f"Maximum attempts reached, pushing to error queue...")
            push_to_error_queue(from_, to, cc, subject, bcc, message, attachments)

        raise self.retry(countdown=30 * 2, exc=exc, max_retries=3)


def push_to_error_queue(from_, to, cc, subject, bcc, message, attachments):
    if broker_host:
        body = dict(
            from_=from_,
            to=to,
            cc=cc,
            subject=subject,
            bcc=bcc,
            message=message,
            attachments=attachments
        )

        # to bytes
        body_bytes = json.dumps(body).encode('utf-8')

        # to decode
        # json.loads(res_bytes.decode('utf-8'))

        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host))
        channel = connection.channel()
        channel.basic_publish(exchange=EMAIL_ERROR_EXCHANGE, routing_key=EMAIL_ERROR_ROUTING_KEY,
                              body=body_bytes)
        connection.close()
