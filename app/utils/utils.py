import random
import string
from datetime import datetime, timezone
from typing import List, Union

import pytz
from passlib.context import CryptContext
from sqlalchemy import and_, asc, desc, or_
from sqlalchemy.orm import Session

import app.models as models
from app.oauth2 import decode_access_token
from app.schemas import schemas

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

    user = db.query(models.Users).filter(
        and_(models.Users.email == email, models.Users.is_validated == True)
    )  # noqa: E712
    if user:
        return True

    return False


def is_user_logged(db: Session, username: str) -> bool:

    response: models.TokenTable = (
        db.query(models.TokenTable)
        .join(models.Users, models.Users.id == models.TokenTable.user_id)
        .filter(models.Users.username == username)
        .order_by(desc(models.TokenTable.created_at))
    )

    if response.status and response:
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


def is_username_email_taken(
    db: Session, username: str, email: str
) -> models.Users | None:
    """Check for an existing username or email

    Args:
        db (Session): Database connection
        username (str): Username
        email (str): Email

    Returns:
        models.Users | None: Field value if found
    """

    user = (
        db.query(models.Users.email).filter(models.Users.email == email).first()
        is not None
    )  # noqa: E712
    if user:
        return user
    return (
        db.query(models.Users.username)
        .filter(models.Users.username == username)
        .first()
        is not None
    )  # noqa: E712


def is_account_unverified(db: Session, email: str, username: str):
    """Check if account is unverified

    Args:
        db (Session): Database connection
        email (str): Email
        username (str): Username

    Returns:
        _type_: User if exists or None
    """

    return (
        db.query(models.Users)
        .filter(
            and_(
                models.Users.email == email,
                models.Users.is_validated == False,  # noqa: E712
                models.Users.username == username,
            )
        )
        .first()
        is not None
    )


def is_code_valid(db: Session, code: int, email: str) -> Union[bool, str]:
    """Check if code has not expired and still exists

    Args:
        db (Session): _description_
        code (int): Code to check
        email (str): Email

    Returns:
        Union[bool, str]: True if valid, False if not
    """

    fetched_record = (
        db.query(models.Users)
        .filter(and_(models.Users.code == code, models.Users.email == email))
        .first()
    )  # noqa: E712

    if not fetched_record or not fetched_record.code_expiration:
        return {"status": "error", "details": "Code not found"}
    if fetched_record.code_expiration < datetime.now(timezone.utc):
        return {"status": "error", "details": "Expired code"}

    return {"status": "success", "details": "Verified code"}


def is_code_expired(db: Session, email: str, code: int) -> bool:

    fetched_record = (
        db.query(models.Users)
        .filter(and_(models.Users.code == code, models.Users.email == email))
        .first()
    )
    if fetched_record and fetched_record.code_expiration > datetime.now(timezone.utc):
        return True
    return False


def is_location_address(location: str) -> bool:
    """Check if a location is given as an address or coordinate

    Args:
        location (str): Input location

    Returns:
        bool: True if address, False if coordinates
    """

    return isinstance(location, str)


def generate_code(db: Session) -> int:
    """Generates unique random code

    Args:
        db (Session): Database connection

    Returns:
        int: Code
    """
    while True:
        validation_code = ""
        validation_code = "".join(random.choices(string.digits, k=6))
        if (
            not db.query(models.Users)
            .filter(and_(models.Users.code == validation_code))
            .first()
        ):  # noqa: E712
            break

    return validation_code


def split_dict_to_array(input_dict: dict[int, datetime]) -> list[datetime]:
    start, end = [], []
    for day in input_dict.values():
        start.append(day[0][0])
        end.append(day[0][1])
    return start, end


def split_array_to_dict(array: list, freq: int) -> dict[int, datetime]:
    return {
        i: array[i * freq : (i + 1) * freq]
        for i in range((len(array) + freq - 1) // freq)
    }
