"""
Email Sender
"""
# pylint: disable=no-name-in-module
from pydantic import BaseModel, validator, EmailStr


# pylint: disable=too-few-public-methods
class EmailSender(BaseModel):
    """
    Represents an Email Sender
    """
    email: EmailStr
    name: str

    @validator("name")
    # pylint: disable=no-self-argument
    def name_must_be_valid(cls, name):
        """
        Validates name of sender
        """
        if name == "":
            raise ValueError("name must not be empty")
        return name
