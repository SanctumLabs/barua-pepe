from app.exceptions import AppException


class EmailSendingException(AppException):
    def __init__(self, message=None):
        if message is None:
            self.message = "Failed to send email message"


class ServiceIntegrationException(AppException):
    def __init__(self, message=None):
        if message is None:
            self.message = "Service Integration Error"
