"""
Configurations for application. These are global variables that the app will use in its entire
lifetime
"""
from functools import lru_cache
from typing import Optional, AnyStr
from pydantic import BaseSettings

from dotenv import load_dotenv

load_dotenv()


def load_from_file(path: str, mode: str, encoding: str) -> AnyStr:
    """
    Convenience function that reads contents of a file
    @param path file path
    @param mode file mode to use when opening file
    @param encoding file encoding
    @returns contents of the file
    """
    with open(file=path, mode=mode, encoding=encoding) as file:
        return file.read()


# pylint: disable=too-few-public-methods
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
    docs_disabled: bool = False

    # smtp settings
    mail_smtp_enabled: bool = True
    mail_server: str = "localhost"
    mail_port: int = 1025
    mail_use_tls: bool = False
    mail_use_ssl: bool = False
    mail_username: str = "baruapepe"
    mail_password: str = "password"

    # mail api settings
    mail_api_token: str = ""
    mail_api_url: str = ""

    result_backend: Optional[str] = "rpc://"

    # sentry settings
    sentry_dsn: str = ""
    sentry_enabled: bool = False
    sentry_traces_sample_rate: float = 0.5

    # security settings
    username: str = "barua-pepe-user"
    password: str = "barua-pepe-password"


config = Config()


@lru_cache()
def get_config():
    """
    Gets configuration This is wrapped with lru_cache to ensure we don't continuously read from .env file on restarts
    """
    return Config()
