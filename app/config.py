from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    """ Database setting parameters structure """
    
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int 
    email: str
    email_password: str
    smtp_server: str
    smtp_port: int
    domain: str
    email_code_expire_minutes: int 
    
    #NOTE: Names must match the ones in .env file

    model_config = {
        "env_file": os.path.join(Path(__file__).resolve().parent.parent, ".env"),
        "env_file_encoding": "utf-8",  # Optional: specify the encoding
    }

settings = Settings()
