from abc import ABC, abstractmethod
from typing import Dict, List


class EmailService(ABC):
    """
    Email Service wrapper around an email service provider
    """

    def __init__(self):
        pass

    @abstractmethod
    def send_email(
        self,
        sender: Dict[str, str],
        recipients: List[Dict[str, str]],
        cc: List[Dict[str, str]] | None,
        bcc: List[Dict[str, str]] | None,
        subject: str,
        message: str,
        attachments: List[Dict[str, str]] | None,
    ):
        raise NotImplementedError("send_email not yet implemented")
