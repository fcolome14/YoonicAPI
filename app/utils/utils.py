from app.responses import SystemResponse, InternalResponse
from app.schemas.schemas import ResponseStatus
import inspect

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


def hash_password(pwd: str) -> InternalResponse:
    """Generates a hashed password

    Args:
        pwd (str): Plain password

    Returns:
        _type_: Hashed password
    """
    origin = inspect.stack()[0].function
    message = pwd_context.hash(pwd)
    return SystemResponse.internal_response(
        ResponseStatus.SUCCESS, origin, message)


def is_password_valid(plain_password: str, hash_password: str) -> dict:
    """Verifies a given plain password is valid

    Args:
        plain_password (str): Password to check
        hash_password (str): Hashed password

    Returns:
        bool: True or False if matches
    """
    origin = inspect.stack()[0].function
    result = pwd_context.verify(plain_password, hash_password)
    
    status=ResponseStatus.SUCCESS
    message="Accepted password"
    if not result:
        status=ResponseStatus.ERROR
        message="Invalid password"
        
    return SystemResponse.internal_response(status, origin, message)


def is_password_strong(plain_password: str) -> InternalResponse:
    """Check password strength.
    At least 8 char and 1 number

    Args:
        plain_password (str): Plain password

    Returns:
        bool: True/False if is valid
    """

    status = ResponseStatus.SUCCESS
    origin = inspect.stack()[0].function
    
    if len(plain_password) < 8:
        message = "Short password"
        return SystemResponse.internal_response(status, origin, message)
    if not any(char.isdigit() for char in plain_password):
        message = "No digits in password"
        return SystemResponse.internal_response(status, origin, message)
    if not any(char.isalpha() for char in plain_password):
        message = "No characters in password"
        return SystemResponse.internal_response(status, origin, message)
    return SystemResponse.internal_response(status, origin, "")


def is_location_address(location: str) -> InternalResponse:
    origin = inspect.stack()[0].function
    result = isinstance(location, str)
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, result)

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
