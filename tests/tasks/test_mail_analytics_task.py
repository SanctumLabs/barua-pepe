from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.domain.entities import EmailRequest
from app.tasks.mail_analytics_task import mail_analytics_task


@patch("app.tasks.mail_analytics_task.send_plain_mail")
def test_analytics_task_validates_legacy_message_before_delivery(send_plain_mail_patch):
    mail_analytics_task(
        data={
            "sender": {"email": "sender@example.com"},
            "recipients": ["to@example.com"],
            "ccs": ["cc@example.com"],
            "bcc": ["bcc@example.com"],
            "subject": "A subject",
            "message": "A message",
        }
    )

    request = send_plain_mail_patch.call_args.args[0]
    assert isinstance(request, EmailRequest)
    assert str(request.recipients[0].email) == "to@example.com"
    assert str(request.ccs[0].email) == "cc@example.com"
    assert str(request.bccs[0].email) == "bcc@example.com"


@patch("app.tasks.mail_analytics_task.send_plain_mail")
def test_analytics_task_rejects_invalid_message(send_plain_mail_patch):
    with pytest.raises(ValidationError):
        mail_analytics_task(
            data={
                "sender": {"email": "sender@example.com"},
                "recipients": [],
                "subject": "A subject",
                "message": "A message",
            }
        )

    send_plain_mail_patch.assert_not_called()
