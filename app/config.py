import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin.auth import verify_id_token
from pydantic_settings import BaseSettings

bearer_scheme = HTTPBearer(auto_error=False)


class Settings(BaseSettings):
    """Database and application settings read from environment variables"""

    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    refresh_secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    email: str
    email_password: str
    smtp_server: str
    smtp_port: int
    domain: str
    email_code_expire_minutes: int
    google_application_credentials: str
    nominatim_base_url: str
    user_agent: str

    class Config:
        env_file = os.path.join(Path(__file__).resolve().parent.parent, ".env")
        env_file_encoding = "utf-8"


settings = Settings()


class FirebaseSettings(BaseSettings):
    """Settings for Firebase authentication"""

    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    refresh_secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    email: str
    email_password: str
    smtp_server: str
    smtp_port: int
    domain: str
    email_code_expire_minutes: int
    google_application_credentials: str
    nominatim_base_url: str
    user_agent: str

    class Config:
        env_file = os.path.join(Path(__file__).resolve().parent.parent, ".env")
        env_file_encoding = "utf-8"


firebase_settings = FirebaseSettings()


def get_firebase_user_from_token(
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
) -> dict | None:
    """Uses bearer token to identify Firebase user ID"""
    try:
        if not token:
            raise ValueError("No token provided")
        user = verify_id_token(token.credentials)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not logged in or Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
