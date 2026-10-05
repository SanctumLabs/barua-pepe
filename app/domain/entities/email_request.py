"""
Email Request
"""
from typing import Any, List, Mapping

# pylint: disable=no-name-in-module
from pydantic import BaseModel, validator
from .email_sender import EmailSender
from .email_attachment import EmailAttachment
from .email_recipient import EmailRecipient


# pylint: disable=too-few-public-methods
class EmailRequest(BaseModel):
    """
    Provider-neutral email request. ``recipients``, ``ccs``, and ``bccs``
    represent the To, CC, and BCC recipient roles respectively.
    """

    sender: EmailSender
    recipients: List[EmailRecipient]
    ccs: List[EmailRecipient] | None = None
    bccs: List[EmailRecipient] | None = None
    subject: str
    message: str
    attachments: List[EmailAttachment] | None = None

    @validator("subject")
    # pylint: disable=no-self-argument
    def subject_must_be_valid(cls, sub):
        """Validates subject"""
        if len(sub) == 0:
            raise ValueError("subject must not be empty")
        return sub

    @validator("message")
    # pylint: disable=no-self-argument
    def message_must_be_valid(cls, mes):
        """Validates message"""
        if len(mes) == 0:
            raise ValueError("message must not be empty")
        return mes

    @validator("recipients")
    # pylint: disable=no-self-argument
    def to_recipients_must_not_be_empty(cls, recipients):
        """Requires at least one To recipient."""
        if not recipients:
            raise ValueError("recipients must not be empty")
        return recipients

    @validator("ccs", "bccs", "attachments")
    # pylint: disable=no-self-argument
    def optional_lists_must_not_be_empty(cls, items):
        """Rejects explicitly supplied empty optional lists."""
        if items is not None and not items:
            raise ValueError("must not be empty")
        return items

    @classmethod
    def from_task_payload(cls, payload: Mapping[str, Any]) -> "EmailRequest":
        """Validates a serialized Celery payload and normalizes legacy keys."""
        values = dict(payload)
        if "ccs" not in values and "cc" in values:
            values["ccs"] = values.pop("cc")
        if "bccs" not in values and "bcc" in values:
            values["bccs"] = values.pop("bcc")
        return cls.parse_obj(values)

    def to_task_payload(self) -> dict[str, Any]:
        """Serializes using the field names used by existing Celery messages."""
        return self.dict()
