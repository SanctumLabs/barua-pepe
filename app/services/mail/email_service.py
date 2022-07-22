"""
Abstract Email Service
"""
from abc import ABC, abstractmethod
from typing import Dict, List


# pylint: disable=too-few-public-methods
class EmailService(ABC):
    """
    Email Service wrapper around an email service provider
    """

    def __init__(self):
        pass

    @abstractmethod
    # pylint: disable=too-many-arguments
    def send_email(
        self,
        sender: Dict[str, str],
        recipients: List[Dict[str, str]],
        ccs: List[Dict[str, str]] | None,
        bcc: List[Dict[str, str]] | None,
        subject: str,
        message: str,
        attachments: List[Dict[str, str]] | None,
    ):
        """
        Sends emails
        """
        raise NotImplementedError("send_email not yet implemented")
