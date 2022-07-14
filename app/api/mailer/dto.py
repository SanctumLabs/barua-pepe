from typing import List
from pydantic import BaseModel, validator, EmailStr, Field


class EmailSenderDto(BaseModel):
    email: EmailStr
    name: str

    @validator("name")
    def name_must_be_valid(cls, n):
        if n == "":
            raise ValueError("must not be empty")
        return n


class EmailAttachmentDto(BaseModel):
    content: str
    filename: str

    @validator("content")
    def subject_must_be_valid(cls, s):
        if len(s) == 0:
            raise ValueError("must not be empty")
        return s

    @validator("filename")
    def message_must_be_valid(cls, m):
        if len(m) == 0:
            raise ValueError("must not be empty")
        return m


class EmailRequestDto(BaseModel):
    from_: EmailSenderDto = Field(alias="from")
    to: List[EmailStr]
    cc: List[EmailStr] | None
    bcc: List[EmailStr] | None
    subject: str
    message: str
    attachments: List[EmailAttachmentDto] | None

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


class EmailResponseDto(BaseModel):
    status: int
    message: str
