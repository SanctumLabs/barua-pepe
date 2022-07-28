"""
Email Participant
"""
# pylint: disable=no-name-in-module
from pydantic import BaseModel, EmailStr


# pylint: disable=too-few-public-methods
class EmailRecipient(BaseModel):
    """
    Represents an email Recipient
    """

    email: EmailStr
    name: str | None
