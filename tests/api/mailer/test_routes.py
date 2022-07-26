import unittest
from unittest.mock import patch
import pytest
from tests import BaseTestCase
from app.exceptions import AppException
import os

base_url = "/api/v1/baruapepe/sendmail/"

os.environ.update(BROKER_URL="memory://", RESULT_BACKEND="rpc")


class TestMailApi(BaseTestCase):
    """
    Test Mail API
    """

    @pytest.mark.anyio
    async def test_throws_405_with_invalid_get_request(self):
        """Test email api throws 405 with invalid http get request"""
        async with self.async_client as ac:
            response = await ac.get(base_url)

        self.assertEqual(405, response.status_code)

    @pytest.mark.anyio
    async def test_throws_405_with_invalid_patch_request(self):
        """Test email api throws 405 with invalid http patch request"""
        async with self.async_client as ac:
            response = await ac.patch(base_url)
        self.assertEqual(405, response.status_code)

    @pytest.mark.anyio
    async def test_throws_405_with_invalid_put_request(self):
        """Test email api throws 405 with invalid http put request"""
        async with self.async_client as ac:
            response = await ac.put(base_url)

        self.assertEqual(405, response.status_code)

    @pytest.mark.anyio
    async def test_throws_400_with_missing_json_body(self):
        """Test email api throws 400 with missing JSON body"""
        async with self.async_client as ac:
            response = await ac.post(base_url)

        response_data = response.json

        self.assertEqual(400, response.status_code)
        self.assertEqual("No data provided", response_data.get("message"))

    @pytest.mark.anyio
    async def test_throws_422_with_missing_required_fields_in_body(self):
        """Test email api throws 422 with missing 'message' in JSON body"""
        async with self.async_client as ac:
            response = await ac.post(base_url,
                                     data=dict(
                                         to=["johndoe@example.com"],
                                         subject="Rocket Schematics!",
                                     )
                                     )

        response_json = response.json

        self.assertEqual(422, response.status_code)
        self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    async def test_throws_422_with_missing_to_required_field_in_body(self):
        """Test email api throws 422 with missing to in JSON body"""
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json=dict(
                    message="Let us do this!",
                    subject="Rocket Schematics!",
                )
            )

            response_json = response.json

        self.assertEqual(422, response.status_code)
        self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    async def test_throws_422_with_missing_subject_in_body(self):
        """Test email api throws 422 with missing 'subject' in JSON body"""
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@example.com"],
                    message="Let's build this!!"
                )
            )

        response_json = response.json

        self.assertEqual(422, response.status_code)
        self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    async def test_throws_422_with_invalid_email_in_to_in_body(self):
        """Test email api throws 422 with an invalid email in 'to' in JSON body"""
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@gmail"],
                    subject="Rocket Schematics!",
                    message="Let's build this!!"
                )
            )

        response_json = response.json

        self.assertEqual(422, response.status_code)
        self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    async def test_throws_422_with_invalid_length_of_subject_in_body(self):
        """Test email api throws 422 with an invalid length of subject in JSON body"""
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@gmail"],
                    subject="",
                    message="Let's build this!!"
                )
            )

        response_json = response.json

        self.assertEqual(422, response.status_code)
        self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    async def test_throws_422_with_invalid_length_of_message_in_body(self):
        """Test email api throws 422 with an invalid length of message in JSON body"""
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@example.com"],
                    subject="Rocket Schematics",
                    message=""
                )
            )
        response_json = response.json

        self.assert_status(actual=response.status_code, status_code=422)
        self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    async def test_throws_422_with_invalid_length_from_in_body_if_provided(self):
        """Test email api throws 422 with an invalid from in JSON body if it is provided"""
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json={
                    "from_": {
                        "email": "ninja",
                    },
                    "to": ["johndoe@example.com"],
                    "cc": ["janedoe@example.com"],
                    "subject": "Rocket Schematics",
                    "message": "Let us build a rocket to the Moon"
                }
            )
        response_json = response.json

        self.assert_status(actual=response.status_code, status_code=422)
        self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    async def test_throws_422_with_invalid_length_of_cc_in_body(self):
        """Test email api throws 422 with an invalid cc length in JSON body and invalid email in cc"""
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@example.com"],
                    cc=[],
                    subject="Rocket Schematics",
                    message="Let us build a rocket to the Moon"
                )
            )

            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=422)
            self.assertIsNotNone(response_json.get("errors"))

            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@example.com"],
                    cc=["janedoe@gmail"],
                    subject="Rocket Schematics",
                    message="Let us build a rocket to the Moon"
                )
            )
            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=422)
            self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    async def test_throws_422_with_invalid_length_of_bcc_in_body(self):
        """Test email api throws 422 with an invalid bcc length in JSON body and invalid email in bcc"""
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@example.com"],
                    cc=["janedoe@example.com"],
                    bcc=[],
                    subject="Rocket Schematics",
                    message="Let us build a rocket to the Moon"
                )
            )
            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=422)
            self.assertIsNotNone(response_json.get("errors"))

            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@example.com"],
                    cc=["janedoe@example.com"],
                    bcc=["hiddenhooman@gmail"],
                    subject="Rocket Schematics",
                    message="Let us build a rocket to the Moon"
                )
            )
            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=422)
            self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    async def test_throws_422_with_invalid_length_of_to_in_body(self):
        """Test email api throws 422 with an invalid to length in JSON body"""
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json=dict(
                    to=[],
                    cc=["janedoe@example.com"],
                    bcc=["hiddenhooman@example.com"],
                    subject="Rocket Schematics",
                    message="Let us build a rocket to the Moon"
                )
            )
            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=422)
            self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    async def test_throws_422_with_invalid_length_of_attachments_in_body(self):
        """Test email api throws 422 with an invalid attachments length in JSON body and missing fields in
        attachments """
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@example.com"],
                    cc=["janedoe@example.com"],
                    bcc=["hiddenhooman@example.com"],
                    subject="Rocket Schematics",
                    message="Let us build a rocket to the Moon",
                    attachments=[]
                )
            )

            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=422)
            self.assertIsNotNone(response_json.get("errors"))

            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@example.com"],
                    cc=["janedoe@example.com"],
                    bcc=["hiddenhooman@example.com"],
                    subject="Rocket Schematics",
                    message="Let us build a rocket to the Moon",
                    attachments=[
                        dict(
                            content="random_string"
                        )
                    ]
                )
            )

            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=422)
            self.assertIsNotNone(response_json.get("errors"))

            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@example.com"],
                    cc=["janedoe@example.com"],
                    bcc=["hiddenhooman@example.com"],
                    subject="Rocket Schematics",
                    message="Let us build a rocket to the Moon",
                    attachments=[
                        dict(
                            filename="rocket_schematics.pdf"
                        )
                    ]
                )
            )

            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=422)
            self.assertIsNotNone(response_json.get("errors"))

            response = await ac.post(
                base_url,
                json=dict(
                    to=["johndoe@example.com"],
                    cc=["janedoe@example.com"],
                    bcc=["hiddenhooman@example.com"],
                    subject="Rocket Schematics",
                    message="Let us build a rocket to the Moon",
                    attachments=[
                        dict(
                            content="random_string",
                            filename="rocket_schematics.pdf"
                        ),
                        dict(
                            filename="rocket_parts.pdf"
                        )
                    ]
                )
            )

            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=422)
            self.assertIsNotNone(response_json.get("errors"))

    @pytest.mark.anyio
    @patch("app.domain.send_email.send_email", return_value=dict(success=True))
    async def test_returns_200_with_valid_json_body(self, mock_sending_task):
        """Test email api returns 200 with an valid JSON body calling send plain email use case"""
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json={
                    "from_": {
                        "email": "ninja@example.com"
                    },
                    "to": ["johndoe@example.com"],
                    "cc": ["janedoe@example.com"],
                    "bcc": ["hiddenhooman@example.com"],
                    "subject": "Rocket Schematics",
                    "message": "Let us build a rocket to the Moon",
                    "attachments": [
                        dict(
                            content="random_string",
                            filename="rocket_schematics.pdf"
                        ),
                    ]
                }
            )

            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=200)
            self.assertEqual("Email sent out successfully", response_json.get("message"))

    @pytest.mark.anyio
    @patch("app.domain.send_email.send_email", side_effect=AppException("Boom!"))
    async def test_returns_500_with_valid_json_body_but_task_fails(self, mock_sending_task):
        """Test email api returns 500 with an valid JSON body calling send plain email use case but exception is
        thrown """
        async with self.async_client as ac:
            response = await ac.post(
                base_url,
                json={
                    "from_": {
                        "email": "ninja@example.com",
                        "name": "Ninja"
                    },
                    "to": ["johndoe@example.com"],
                    "cc": ["janedoe@example.com"],
                    "bcc": ["hiddenhooman@example.com"],
                    "subject": "Rocket Schematics",
                    "message": "Let us build a rocket to the Moon",
                    "attachments": [
                        dict(
                            content="random_string",
                            filename="rocket_schematics.pdf"
                        ),
                    ]
                }
            )

            response_json = response.json

            self.assert_status(actual=response.status_code, status_code=500)
            self.assertEqual("Failed to send email", response_json.get("message"))


if __name__ == '__main__':
    unittest.main()
