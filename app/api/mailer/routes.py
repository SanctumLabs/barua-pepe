from fastapi import APIRouter
from app.logger import log as logger
from .dto import EmailRequestDto, EmailResponseDto
from app.api.dto import ApiResponse, BadRequest
from app.exceptions import EmailGatewayError
from app.tasks.mail_sending_task import mail_sending_task
from starlette import status

router = APIRouter(tags=["Email"])


@logger.catch
@router.post(path="/sendmail", summary="Send Email", description="Sends an email", response_model=EmailResponseDto)
async def send_plain_email(payload: EmailRequestDto):
    """
    Send email API function. This is a POST REST endpoint that accepts requests that meet the criteria defined by the
    schema validation before sending a plain text email
    :return: JSON response to client
    :rtype: dict
    """

    if not payload:
        return BadRequest(message="No data provided")

    try:
        mail_sending_task.apply_async(
            kwargs=dict(
                from_=payload.from_,
                to=payload.to,
                cc=payload.cc,
                subject=payload.subject,
                bcc=payload.bcc,
                message=payload.message,
                attachments=payload.attachments
            ))

        return ApiResponse(
            status=status.HTTP_200_OK,
            message="Email sent out successfully"
        )
    except EmailGatewayError as e:
        logger.error(f"Failed to send email to {payload.to} with error {e}")
        return ApiResponse(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to send email"
        )
