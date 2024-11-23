from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import app.models as models
from typing import Union
import pytz
from datetime import datetime, timedelta
from app.config import settings
import random
import string

utc = pytz.UTC

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(pwd: str):
    """Generates a hashed password

    Args:
        pwd (str): Plain password

    Returns:
        _type_: Hashed password
    """
    
    return pwd_context.hash(pwd)


def is_password_valid(plain_password: str, hash_password: str) -> bool:
    """Verifies a given plain password is valid

    Args:
        plain_password (str): Password to check
        hash_password (str): Hashed password

    Returns:
        bool: True or False if matches
    """
    
    return pwd_context.verify(plain_password, hash_password)


def is_user_valid(db: Session, email: str) -> models.Users | None:
    """Verifies if a user has been validated before

    Args:
        db (Session): Database connection
        email (str): Email
        password (str): Plain password

    Returns:
        models.Users | None: User records if its validates
    """
    
    user = db.query(models.Users).filter(and_(models.Users.email == email,  
                                               models.Users.is_validated == True))  # noqa: E712
    if user:
        return True
    
    return False

def is_user_logged(db: Session, username: str) -> bool:
    
    response = db.query(models.TokenTable).join(models.Users, models.Users.id == models.TokenTable.user_id).filter(models.Users.username == username).first()
    
    if response:
        return True
    return False



def is_password_strong(plain_password: str) -> bool:
    """Check password strength. 
    At least 8 char and 1 number

    Args:
        plain_password (str): Plain password

    Returns:
        bool: True/False if is valid
    """
    
    if len(plain_password) < 8:
        return False
    if not any(char.isdigit() for char in plain_password):
        return False
    if not any(char.isalpha() for char in plain_password):
        return False 
    return True 


def is_username_taken(db: Session, username: str):
    """Checks if a username already exists

    Args:
        db (Session): Database connection
        username (str): Username to check

    Returns:
        _type_: User if exists or None
    """
    
    return db.query(models.Users).filter(models.Users.username == username).first() is not None  # noqa: E712


def is_account_unverified(db: Session, email: str, username: str):
    """Check if account is unverified

    Args:
        db (Session): Database connection
        email (str): Email
        username (str): Username

    Returns:
        _type_: User if exists or None
    """
    
    return db.query(models.Users).filter(and_(models.Users.email == email, 
                                              models.Users.is_validated == False,  # noqa: E712
                                              models.Users.username == username)).first() is not None

def is_code_valid(db: Session, code: int, email: str) -> Union[bool, str]:
    """Check if code has not expired and still exists

    Args:
        db (Session): Database connection
        code (int): Code to check

    Returns:
        bool: True if valid, False if not
    """
    
    fetched_record = db.query(models.Users).filter(and_(models.Users.code == code, models.Users.email == email)).first()  # noqa: E712
    
    if not fetched_record or not fetched_record.code_expiration:
        return {"status": "error", "details": "Code not found"}
    if fetched_record.code_expiration < datetime.utcnow().replace(tzinfo=utc):
        return {"status": "error", "details": "Expired code"}
    
    return {"status": "success", "details": "Verified code"}


def generate_code(db: Session) -> int:
    """Generates unique random code

    Args:
        db (Session): Database connection

    Returns:
        int: Code
    """
    while True:
        validation_code = ""
        validation_code = ''.join(random.choices(string.digits, k=6))
        if not db.query(models.Users).filter(and_(models.Users.code == validation_code)).first():  # noqa: E712
            break
        
    return validation_code