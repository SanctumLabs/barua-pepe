"""
Abstract Email Service
"""

from abc import ABC, abstractmethod
from typing import TypedDict

from app.domain.entities import EmailRequest


class EmailDeliveryResult(TypedDict):
    """Provider-neutral result returned after a provider accepts a request."""

    success: bool
    message: str


# pylint: disable=too-few-public-methods
class EmailService(ABC):
    """
    Email Service wrapper around an email service provider
    """

    def __init__(self):
        pass

    @abstractmethod
    def send_email(self, request: EmailRequest) -> EmailDeliveryResult:
        """
        Submits a canonical email request to the provider.
        """
        raise NotImplementedError("send_email not yet implemented")
