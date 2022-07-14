import unittest
from tests import BaseTestCase
from unittest.mock import patch, Mock, MagicMock
from app.services.email import send_plain_mail


class EmailTestCases(BaseTestCase):
    """
    Email test cases
    """

    # test values to use
    from_ = "ninja@example.com"
    to = ["johndoe@example.com", "janedoe@example.com"]
    bcc = ["hiddenspy@mischevious.com"]
    cc = ["buzzer@rocket.com"]
    subject = "Rocket Ship Schematics"
    message = "We need to start setting up the rocket ship plans"
    attachments = [
        {
            "filename": "schematics.pdf",
            "content": "abcdef"
        }
    ]

    def setUp(self):
        # self.mock_mail = Mail()
        self.mock_mail.send = MagicMock()
        self.requests = Mock()

    def tearDown(self):
        self.mock_mail = None

    def post_request(self, url):
        # Create a new Mock to imitate a Response
        response_mock = Mock()
        response_mock.status_code = 200

        return response_mock

    def test_uses_default_email_sender_to_send_email(self):
        """Test default email sender is used when required parameters are used"""
        # with self.app.app_context():
        #     # mock Message from flask mailer
        #     mock_message = Message(
        #         sender=self.from_,
        #         subject=self.subject,
        #         recipients=self.to,
        #         cc=self.cc,
        #         bcc=self.bcc,
        #         body=self.message
        #     )
        #
        #     # send a plain email
        #     response = send_plain_mail(
        #         to=self.to,
        #         subject=self.subject,
        #         message=self.message,
        #     )
        #
        #     # mock sending out the email
        #     self.mock_mail.send(mock_message)
        #
        #     # assert that the call count is increased, meaning the default mail sender is used
        #     self.assertEqual(self.mock_mail.send.call_count, 1)
        #     self.mock_mail.send.assert_called_with(mock_message)
        #     self.assertTrue(response.get("success"))
        #     self.assertEqual(response.get("message"), "Message successfully sent")

    def test_uses_fallback_when_default_email_sender_fails(self):
        """Test uses fallback email sender when default email sender fails"""
        # with self.app.app_context():
        #     # mock Message from flask mailer
        #     mock_message = Message(
        #         sender=self.from_,
        #         subject=self.subject,
        #         recipients=self.to,
        #         cc=self.cc,
        #         bcc=self.bcc,
        #         body=self.message
        #     )
        #
        #     self.mock_mail.send = MagicMock(side_effect=Exception("Failed to send email message"))
        #
        #     # send a plain email
        #     send_plain_mail(
        #         to=self.to,
        #         subject=self.subject,
        #         message=self.message,
        #     )
        #
        #     # mock sending out the email, should throw an error
        #     try:
        #         self.mock_mail.send(mock_message)
        #     except Exception:
        #         # test that default method is used
        #         recipients_to = [{"email": email} for email in self.to]
        #
        #         request_body = {
        #             "personalizations": [
        #                 recipients_to
        #             ],
        #             "from": {
        #                 "email": self.from_
        #             },
        #             "subject": self.subject,
        #             "content": [
        #                 {
        #                     "type": "text/html",
        #                     "value": self.message
        #                 }
        #             ]
        #         }
        #
        #         self.requests.post = MagicMock()
        #         self.requests.post(json=request_body)
        #         self.assertEqual(self.requests.post.call_count, 1)


if __name__ == '__main__':
    unittest.main()
