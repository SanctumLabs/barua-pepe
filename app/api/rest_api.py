from . import mail_api
from flask import jsonify, request
from app.logger import log as logger
from .schemas import EmailMessageSchema
from app.exceptions import EmailGatewayError
from app.tasks.mail_sending_task import mail_sending_task
from marshmallow.exceptions import ValidationError

email_message_schema = EmailMessageSchema()


@logger.catch
@mail_api.route("/", methods=["POST"])
def send_plain_email():
    """
    Send email API function. This is a POST REST endpoint that accepts requests that meet the criteria defined by the
    schema validation before sending a plain text email
    :return: JSON response to client
    :rtype: dict
    """
    payload = request.get_json()

    if not payload:
        return jsonify(dict(message="No data provided")), 400

    if payload.get("from"):
        payload.update({"from_": payload.get("from")})

    try:
        # validate JSON body
        data = email_message_schema.load(payload)

        try:
            mail_sending_task.apply_async(
                kwargs=dict(
                    from_=data.get("from_"),
                    to=data.get("to"),
                    cc=data.get("cc"),
                    subject=data.get("subject"),
                    bcc=data.get("bcc"),
                    message=data.get("message"),
                    attachments=data.get("attachments")
                ))            

            return jsonify(dict(
                message="Email sent out successfully"
            )), 200
        except EmailGatewayError as e:
            logger.error(f"Failed to send email to {payload.get('to')} with error {e}")
            return jsonify(dict(
                success=False,
                message="Failed to send email"
            )), 500
    except ValidationError as ve:
        logger.error(f"Failed to load schema with error {ve}")
        return jsonify(dict(errors=[ve.messages])), 422
