"""
Contains Wrapper around an authentication service
"""
import secrets
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.config import get_config

security = HTTPBasic()

config = get_config()


def get_current_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Gets the current authentication and adds it to the request context
    """
    correct_username = secrets.compare_digest(credentials.username, config.username)
    correct_password = secrets.compare_digest(credentials.password, config.password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials
