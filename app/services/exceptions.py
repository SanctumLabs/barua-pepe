from app.exceptions import EmailGatewayError


class EmailSendingException(EmailGatewayError):
    def __init__(self, message=None):
        if message is None:
            self.message = "Failed to send email message"


class ServiceIntegrationException(EmailGatewayError):
    def __init__(self, message=None):
        if message is None:
            self.message = "Service Integration Error"
