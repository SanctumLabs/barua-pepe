"""
Exceptions for Mail Services
"""
from app.exceptions import AppException


class EmailSendingException(AppException):
    """Exception representing failure to send email"""

    def __init__(self, message=None):
        super().__init__(message or "Failed to send email message")


class ServiceIntegrationException(AppException):
    """Exception representing failure to integrate with 3rd party service"""

    def __init__(self, message=None):
        super().__init__(message or "Service Integration Error")
