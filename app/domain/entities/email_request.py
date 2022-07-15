from typing import List
from .email_sender import EmailSender
from .email_attachment import EmailAttachment
from .email_recipient import EmailRecipient
from pydantic import BaseModel, validator


class EmailRequest(BaseModel):
    sender: EmailSender
    recipient: List[EmailRecipient]
    cc: List[EmailRecipient] | None
    bcc: List[EmailRecipient] | None
    subject: str
    message: str
    attachments: List[EmailAttachment] | None

    @validator("subject")
    def subject_must_be_valid(cls, s):
        if len(s) == 0:
            raise ValueError("must not be empty")
        return s

    @validator("message")
    def message_must_be_valid(cls, m):
        if len(m) == 0:
            raise ValueError("must not be empty")
        return m
