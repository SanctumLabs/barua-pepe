"""
Email Participant
"""
# pylint: disable=no-name-in-module
from pydantic import BaseModel, EmailStr, root_validator


# pylint: disable=too-few-public-methods
class EmailRecipient(BaseModel):
    """
    Represents an email Recipient
    """

    email: EmailStr
    name: str | None = None

    @root_validator(pre=True)
    # pylint: disable=no-self-argument
    def accept_email_address(cls, values):
        """Accept an email address string as shorthand for a recipient object."""
        if isinstance(values, str):
            return {"email": values}
        return values
