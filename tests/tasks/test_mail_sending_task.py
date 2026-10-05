import unittest
from unittest.mock import patch
from celery.exceptions import Retry
import pytest
from pytest import raises
from pydantic import ValidationError
from app.domain.entities import EmailRequest
from app.services.mail.exceptions import DeliveryOutcomeUnknownException
from app.tasks.mail_sending_task import mail_sending_task


@pytest.mark.celery(result_backend="memory://", broker_url="memory://")
class MailSendingTaskTestCases(unittest.TestCase):

    @patch("app.tasks.mail_sending_task.send_plain_mail")
    def test_mail_sending_tasks_sends_plain_email(self, send_plain_mail_patch):
        """Mail Sending Task should call send plain email to send emails"""
        sender = {"email": "johndoe@example.com", "name": "John Doe"}
        recipients = [dict(email="janedoe@example.com", name="Jane Doe")]
        subject = "Hello Jane!"
        message = "Testing 1 2 3"
        ccs = [dict(email="jack@example.com", name="Jack")]
        bcc = [dict(email="spy@example.com", name="Mr Spy")]
        attachments = [
            dict(filename="somefile.png", content="file contents", type="image/png")
        ]

        data = dict(
            sender=sender,
            recipients=recipients,
            ccs=ccs,
            bcc=bcc,
            subject=subject,
            message=message,
            attachments=attachments,
        )

        mail_sending_task(data=data)

        request = send_plain_mail_patch.call_args.args[0]
        self.assertIsInstance(request, EmailRequest)
        self.assertEqual(sender, request.sender.dict())
        self.assertEqual(
            recipients, [recipient.dict() for recipient in request.recipients]
        )
        self.assertEqual(ccs, [recipient.dict() for recipient in request.ccs])
        self.assertEqual(bcc, [recipient.dict() for recipient in request.bccs])
        self.assertEqual(
            attachments, [attachment.dict() for attachment in request.attachments]
        )

    @patch("app.tasks.mail_sending_task.send_plain_mail")
    def test_mail_sending_task_accepts_legacy_payload_without_optional_fields(
        self, send_plain_mail_patch
    ):
        """Legacy messages may omit optional CC, BCC, and attachment fields."""
        data = dict(
            sender={"email": "johndoe@example.com"},
            recipients=["janedoe@example.com"],
            subject="Hello Jane!",
            message="Testing 1 2 3",
        )

        mail_sending_task(data=data)

        request = send_plain_mail_patch.call_args.args[0]
        self.assertIsNone(request.ccs)
        self.assertIsNone(request.bccs)
        self.assertIsNone(request.attachments)
        self.assertEqual("janedoe@example.com", str(request.recipients[0].email))

    @patch("app.tasks.mail_sending_task.send_plain_mail")
    @patch("app.tasks.mail_sending_task.mail_error_task.apply_async")
    def test_mail_sending_task_rejects_invalid_payload_before_delivery(
        self, mail_error_apply_async_patch, send_plain_mail_patch
    ):
        """Invalid queued messages fail validation without attempting delivery."""
        data = dict(
            sender={"email": "johndoe@example.com"},
            recipients=[],
            subject="Hello Jane!",
            message="Testing 1 2 3",
        )

        with raises(ValidationError):
            mail_sending_task(data=data)

        send_plain_mail_patch.assert_not_called()
        mail_error_apply_async_patch.assert_called_once_with(
            kwargs={"data": data, "request_id": None}
        )

    def test_task_payload_serialization_preserves_legacy_keys(self):
        """New messages keep the previously serialized Celery field names."""
        request = EmailRequest.from_task_payload(
            dict(
                sender={"email": "johndoe@example.com", "name": "John Doe"},
                recipients=[{"email": "janedoe@example.com", "name": "Jane Doe"}],
                ccs=[{"email": "jack@example.com", "name": "Jack"}],
                bccs=[{"email": "spy@example.com", "name": "Mr Spy"}],
                subject="Hello Jane!",
                message="Testing 1 2 3",
                attachments=[
                    dict(
                        filename="somefile.png",
                        content="file contents",
                        type="image/png",
                    )
                ],
            )
        )

        payload = request.to_task_payload()

        self.assertIn("recipients", payload)
        self.assertIn("ccs", payload)
        self.assertIn("bccs", payload)
        self.assertNotIn("to", payload)
        self.assertEqual("spy@example.com", payload["bccs"][0]["email"])

    def test_unknown_delivery_outcome_is_not_retried(self):
        """Unknown provider acceptance is routed for inspection, not resubmitted."""
        unknown_outcome = DeliveryOutcomeUnknownException("connection lost")

        class DummyRequest:
            retries = 0
            id = "celery-request-id"

        class DummySelf:
            request = DummyRequest()
            max_retries = 3

            def retry(self, *args, **kwargs):
                raise AssertionError("Unknown outcomes must not be retried")

        data = {
            "sender": {"email": "sender@example.com"},
            "recipients": ["recipient@example.com"],
            "subject": "subject",
            "message": "message",
        }

        with (
            patch(
                "app.tasks.mail_sending_task.send_plain_mail",
                side_effect=unknown_outcome,
            ),
            patch(
                "app.tasks.mail_sending_task.mail_error_task.apply_async"
            ) as error_task_apply_async,
            pytest.raises(DeliveryOutcomeUnknownException) as raised,
        ):
            mail_sending_task.run.__func__(DummySelf(), data, request_id="trace-123")

        assert raised.value is unknown_outcome
        error_task_apply_async.assert_called_once_with(
            kwargs={"data": data, "request_id": "trace-123"}
        )

    def test_other_delivery_failures_still_retry(self):
        """Failures without an unknown outcome retain Celery retry behavior."""
        failure = RuntimeError("temporary provider error")
        retry_args = {}

        class RetryRequested(Exception):
            pass

        class DummyRequest:
            retries = 0
            id = "celery-request-id"

        class DummySelf:
            request = DummyRequest()
            max_retries = 3

            def retry(self, **kwargs):
                retry_args.update(kwargs)
                raise RetryRequested

        data = {
            "sender": {"email": "sender@example.com"},
            "recipients": ["recipient@example.com"],
            "subject": "subject",
            "message": "message",
        }

        with (
            patch("app.tasks.mail_sending_task.send_plain_mail", side_effect=failure),
            patch(
                "app.tasks.mail_sending_task.mail_error_task.apply_async"
            ) as error_task_apply_async,
            pytest.raises(RetryRequested),
        ):
            mail_sending_task.run.__func__(DummySelf(), data, request_id="trace-123")

        assert retry_args == {"countdown": 30, "exc": failure}
        error_task_apply_async.assert_not_called()

    @unittest.skip(
        "self.retry is not raising celery.exceptions.Retry exception. This needs to be investigated further"
    )
    @patch("app.tasks.mail_sending_task.send_plain_mail")
    @patch("app.tasks.mail_sending_task.mail_sending_task.retry")
    def test_mail_sending_task_raises_exception_on_failure(
        self, mail_sending_task_retry, send_plain_mail_patch
    ):
        """Mail Sending Task should retry sending plain email on failure"""
        sender = {"email": "johndoe@example.com", "name": "John Doe"}
        recipients = [dict(email="janedoe@example.com", name="Jane Doe")]
        subject = "Hello Jane!"
        message = "Testing 1 2 3"
        ccs = [dict(email="jack@example.com", name="Jack")]
        bcc = [dict(email="spy@example.com", name="Mr Spy")]
        attachments = [
            dict(filename="somefile.png", content="file contents", type="image/png")
        ]

        data = dict(
            sender=sender,
            recipients=recipients,
            ccs=ccs,
            bcc=bcc,
            subject=subject,
            message=message,
            attachments=attachments,
        )

        # side effect with error
        mail_sending_task_retry.side_effect = Retry()
        send_plain_mail_patch.side_effect = Exception("Failed to send email")

        send_plain_mail_patch.assert_not_called()

        with raises(Retry):
            mail_sending_task(data=data)


if __name__ == "__main__":
    unittest.main()
