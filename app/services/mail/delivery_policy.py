"""Provider selection policy for email delivery attempts."""

from typing import Callable, Protocol

from app.domain.entities import EmailRequest
from .email_service import EmailDeliveryResult
from .exceptions import DeliveryRejectedException, EmailSendingException


# pylint: disable=too-few-public-methods
class EmailProvider(Protocol):
    """Interface for an adapter that submits canonical email requests."""

    def send_email(self, request: EmailRequest) -> EmailDeliveryResult:
        """Submit a request and return the provider result."""


EmailProviderFactory = Callable[[], EmailProvider]


def _submit(
    request: EmailRequest, provider_factory: EmailProviderFactory
) -> EmailDeliveryResult:
    try:
        provider = provider_factory()
    except Exception as error:
        raise DeliveryRejectedException(
            "Email provider could not be initialized before submission"
        ) from error
    return provider.send_email(request)


def deliver_email(
    request: EmailRequest,
    primary: EmailProviderFactory,
    fallback: EmailProviderFactory | None = None,
) -> EmailDeliveryResult:
    """Try fallback only when the primary provider explicitly rejected the request."""
    try:
        return _submit(request, primary)
    except DeliveryRejectedException as primary_error:
        if fallback is None:
            raise EmailSendingException(
                "Primary email provider rejected the request"
            ) from primary_error

        try:
            return _submit(request, fallback)
        except DeliveryRejectedException as fallback_error:
            raise EmailSendingException(
                "Primary and fallback email providers rejected the request"
            ) from fallback_error
