"""
Schemas used to validate API requests sent to the application. These validate based on whether a field is required
or has a valid email format. Uses Marshmallow to handle the schema validation. Refer to this documentation for more on
validation. https://marshmallow.readthedocs.io/en/3.0/
"""
from marshmallow import Schema, fields
from marshmallow.validate import Length, Email


class EmailSenderSchema(Schema):
    """
    Validates the email sender if it is provided
    :cvar email: Email field Required
    :cvar name: Name field
    """

    email = fields.String(validate=Email(error="Not a valid email address"), required=True)
    name = fields.String(required=False, validate=Length(min=1))


class EmailAttachmentSchema(Schema):
    """
    Attachment schema
    :cvar content Content of the attachment as a Base64 encoding
    :cvar filename Name of attachment file
    """
    content = fields.String(required=True, validate=Length(min=1))
    filename = fields.String(required=True, validate=Length(min=1))


class EmailMessageSchema(Schema):
    """
    Email message schema, used to validate the email message
    :cvar from_: Message from which the email is being sent from
    :cvar to: List of valid email to send email message
    :cvar cc: List of valid Carbon copy recipients of email
    :cvar bcc: List of valid Blind Carbon Copy recipients of email
    :cvar attachments: List of attachments to send an email
    :cvar subject: Subject to use for the email message
    :cvar message: Message to use for the email message. This will appear in the content of the body
    """
    from_ = fields.Nested(EmailSenderSchema, required=False)
    to = fields.List(fields.Email(), required=True, validate=Length(min=1))
    cc = fields.List(fields.Email(), required=False, validate=Length(min=1))
    bcc = fields.List(fields.Email(), required=False, validate=Length(min=1))
    subject = fields.String(required=True, validate=Length(min=1))
    message = fields.String(required=True, validate=Length(min=1))
    attachments = fields.List(
        fields.Nested(
            EmailAttachmentSchema,
            required=False,
            validate=Length(min=1)
        ),
        required=False,
        validate=Length(min=1)
    )
