from app.tasks.mail_sending_task import mail_sending_task
from app.domain.entities import EmailRequest


def send_email(request: EmailRequest):
    data = dict(
        sender=request.sender.dict(),
        recipients=[recipient.dict() for recipient in request.recipient],
        cc=[cc.dict() for cc in request.cc] if request.cc else [],
        bcc=[bcc.dict() for bcc in request.bcc] if request.bcc else [],
        subject=request.subject,
        message=request.message,
        attachments=[attachment.dict() for attachment in request.attachments] if request.attachments else []
    )

    mail_sending_task.apply_async(kwargs=data)
