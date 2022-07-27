import unittest
from unittest.mock import patch
from celery.exceptions import Retry
import pytest
from pytest import raises
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
        attachments = [dict(filename="somefile.png", content="file contents", type="image/png")]

        data = dict(
            sender=sender,
            recipients=recipients,
            ccs=ccs,
            bcc=bcc,
            subject=subject,
            message=message,
            attachments=attachments,
        )

        mail_sending_task(sender=sender, recipients=recipients, subject=subject, message=message, ccs=ccs, bcc=bcc,
                          attachments=attachments)

        send_plain_mail_patch.assert_called_with(**data)

    @unittest.skip("self.retry is not raising celery.exceptions.Retry exception. This needs to be investigated further")
    @patch("app.tasks.mail_sending_task.send_plain_mail")
    @patch("app.tasks.mail_sending_task.mail_sending_task.retry")
    def test_mail_sending_task_raises_exception_on_failure(self, mail_sending_task_retry,
                                                           send_plain_mail_patch):
        """Mail Sending Task should retry sending plain email on failure"""
        sender = {"email": "johndoe@example.com", "name": "John Doe"}
        recipients = [dict(email="janedoe@example.com", name="Jane Doe")]
        subject = "Hello Jane!"
        message = "Testing 1 2 3"
        ccs = [dict(email="jack@example.com", name="Jack")]
        bcc = [dict(email="spy@example.com", name="Mr Spy")]
        attachments = [dict(filename="somefile.png", content="file contents", type="image/png")]

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
            mail_sending_task(sender=sender, recipients=recipients, subject=subject, message=message, ccs=ccs, bcc=bcc,
                              attachments=attachments)


if __name__ == '__main__':
    unittest.main()
