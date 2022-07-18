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
    server_name: str = "Barua Pepe"
    description: str = "Simple RESTful Email Server"
    base_url: str = "/api/v1/baruapepe"
    environment: str = "development"

    # smtp settings
    mail_server: str = "localhost"
    mail_port: int = 1025
    mail_use_tls: bool = False
    mail_use_ssl: bool = False
    mail_username: str = os.environ.get('USERNAME', None)
    mail_password: str = os.environ.get('PASSWORD', None)

    # mail api settings
    mail_api_token: str = os.environ.get("MAIL_API_TOKEN", "")
    mail_api_url: str = os.environ.get("MAIL_API_URL", "")
    result_backend: Optional[str] = os.environ.get("RESULT_BACKEND", "rpc://")
    docs_disabled: bool = False

    # sentry settings
    sentry_dsn: str = ""
    sentry_enabled: bool = False
    sentry_traces_sample_rate: float = 0.5


config = Config()
