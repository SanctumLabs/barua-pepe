"""
Use case to send out emails
"""
from app.tasks.mail_sending_task import mail_sending_task
from app.domain.entities import EmailRequest


def send_email(data: EmailRequest):
    """
    Command to send out emails
    """
    mail_sending_task.apply_async(kwargs=dict(data=data.dict()))
