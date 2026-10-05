"""
Use case to send out emails
"""
from app.tasks.mail_sending_task import mail_sending_task
from app.domain.entities import EmailRequest


def send_email(data: EmailRequest, request_id: str | None = None):
    """
    Command to send out emails
    :param data: EmailRequest Pydantic model
    :param request_id: optional request id for tracing from HTTP request
    """
    mail_sending_task.apply_async(
        kwargs={"data": data.to_task_payload(), "request_id": request_id}
    )
