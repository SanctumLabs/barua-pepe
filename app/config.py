"""
Configurations for application. These are global variables that the app will use in its entire
lifetime
"""
import os
from typing import Optional
from pydantic import BaseSettings

from dotenv import load_dotenv

load_dotenv()


def load_from_file(path: str):
    with open(path) as f:
        return f.read()


class Config(BaseSettings):
    """
    Application settings

    You can overwrite any of these settings by having an environment
    variable with the uppercased version of the name
    """
    environment: str = "development"
    mail_server: str = os.environ.get("HOST")
    mail_port: int = os.environ.get("SMTPPORT")
    mail_use_tls: bool = False
    mail_use_ssl: bool = False
    mail_username: str = os.environ.get('USERNAME', None)
    mail_password: str = os.environ.get('PASSWORD', None)
    mail_default_sender: str = os.environ.get("SENDEREMAILADDRESS", None)
    mail_api_token: str = os.environ.get("MAIL_API_TOKEN", "")
    mail_api_url: str = os.environ.get("MAIL_API_URL", "")
    result_backend: Optional[str] = os.environ.get("RESULT_BACKEND", "rpc://")
    docs_disabled: bool = False


config = Config()
