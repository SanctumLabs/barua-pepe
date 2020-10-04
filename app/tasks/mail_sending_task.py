from app import celery_app
from app.logger import log
from app.services.email import send_plain_mail
from app.constants import EMAIL_ERROR_EXCHANGE, EMAIL_ERROR_ROUTING_KEY, EMAIL_ERROR_QUEUE_NAME
from .exceptions import TaskException
import pika
import os
import json

broker_host = os.environ.get("BROKER_HOST")
broker_port = os.environ.get("BROKER_PORT")
broker_username = os.environ.get("BROKER_USER")
broker_password = os.environ.get("BROKER_PASSWORD")

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

        credentials = pika.PlainCredentials(username=broker_username, password=broker_password)

        connection = pika.BlockingConnection(pika.ConnectionParameters(host=broker_host, port=broker_port, credentials=credentials))
        channel = connection.channel()
        channel.confirm_delivery()

        # channel.queue_declare(queue=EMAIL_ERROR_QUEUE_NAME, passive=True)

        # channel.queue_bind(queue=EMAIL_ERROR_QUEUE_NAME, exchange=EMAIL_ERROR_EXCHANGE, routing_key=EMAIL_ERROR_ROUTING_KEY)

        channel.basic_publish(
            exchange=EMAIL_ERROR_EXCHANGE, 
            routing_key=EMAIL_ERROR_ROUTING_KEY,
            body=body_bytes,
            properties=pika.BasicProperties(delivery_mode=2)
        )

        connection.close()
