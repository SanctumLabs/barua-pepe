from app.tasks.mail_sending_task import mail_sending_task
from app.domain.entities import EmailRequest


def send_email(request: EmailRequest):
    mail_sending_task.apply_async(
        kwargs=dict(
            from_=request.sender.dict(),
            to=[recipient.dict() for recipient in request.recipient],
            cc=[cc.dict() for cc in request.cc],
            bcc=[bcc.dict() for bcc in request.bcc],
            subject=request.subject,
            message=request.message,
            attachments=[attachment.dict() for attachment in request.attachments]
        ))
