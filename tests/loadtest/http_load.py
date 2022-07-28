import time
from locust import HttpUser, task, between

base_url = "/api/v1/baruapepe"
username = "barua-pepe-user"
password = "barua-pepe-password"


class BaruaPepeUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def send_email(self):
        self.client.post(f"{base_url}/sendmail", auth=(username, password), json={
            "from": {
                "email": "user@example.com",
                "name": "John Doe"
            },
            "to": [
                {
                    "email": "johndoe@example.com"
                }
            ],
            "cc": [
                {
                    "email": "user@example.com"
                }
            ],
            "bcc": [
                {
                    "email": "user@example.com"
                }
            ],
            "subject": "test subject",
            "message": "test message",
            "attachments": [
                {
                    "content": "string",
                    "filename": "string",
                    "type": "text/plain"
                }
            ]
        })
