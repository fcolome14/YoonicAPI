from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, asc, desc
import app.models as models
from app.oauth2 import decode_access_token
from typing import Union
import pytz
from datetime import datetime, timezone
from app.schemas import schemas
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
    
    response: models.TokenTable = db.query(models.TokenTable).join(
    models.Users, models.Users.id == models.TokenTable.user_id).filter(
    models.Users.username == username).order_by(desc(models.TokenTable.created_at))
    
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


def is_username_email_taken(db: Session, username: str, email: str) -> models.Users | None:
    """Check for an existing username or email

    Args:
        db (Session): Database connection
        username (str): Username
        email (str): Email

    Returns:
        models.Users | None: Field value if found
    """
    
    user = db.query(models.Users.email).filter(models.Users.email == email).first() is not None  # noqa: E712
    if user:
        return user
    return db.query(models.Users.username).filter(models.Users.username == username).first() is not None  # noqa: E712


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
        db (Session): _description_
        code (int): Code to check
        email (str): Email

    Returns:
        Union[bool, str]: True if valid, False if not
    """
    
    fetched_record = db.query(models.Users).filter(and_(models.Users.code == code, models.Users.email == email)).first()  # noqa: E712
    
    if not fetched_record or not fetched_record.code_expiration:
        return {"status": "error", "details": "Code not found"}
    if fetched_record.code_expiration < datetime.now(timezone.utc):
        return {"status": "error", "details": "Expired code"}
    
    return {"status": "success", "details": "Verified code"}

def is_code_expired(db: Session, email: str, code: int) -> bool:
    
    fetched_record = db.query(models.Users).filter(and_(models.Users.code == code, models.Users.email == email)).first()
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
        validation_code = ''.join(random.choices(string.digits, k=6))
        if not db.query(models.Users).filter(and_(models.Users.code == validation_code)).first():  # noqa: E712
            break
        
    return validation_code

def update_post_data(user_id: int, update_data: schemas.UpdatePostInput, db: Session) -> dict:
    """Update post data if there are changes

    Args:
        user_id (int): Owner of the post
        update_data (schemas.UpdatePostInput): Schema with all new data to be updated
        db (Session): Database connection

    Returns:
        dict: Information about failures or successful changes applied
    """
    fetched_posts = db.query(models.Events).filter(and_(models.Events.owner_id == user_id, models.Events.id == update_data.id)).first()
    
    if not fetched_posts:
        return {"status": "error", "details": "Record not found"}
    
    changes_made = False
    
    applied_actions = {}
    
    for field, new_value in update_data.model_dump(exclude_unset=True).items():
        if hasattr(fetched_posts, field):
            current_value = getattr(fetched_posts, field)

            if new_value is not None and current_value != new_value:
                setattr(fetched_posts, field, new_value)
                changes_made = True
                
                if isinstance(current_value, datetime):
                    current_value = current_value.isoformat()
                if isinstance(new_value, datetime):
                    new_value = new_value.isoformat()
                if isinstance(current_value, float):
                    new_value = float(new_value)
                if isinstance(current_value, int):
                    new_value = int(new_value)
                    
                key_old = f'{field}_old'
                key_new = f'{field}_new'
                applied_actions[key_old] = current_value
                applied_actions[key_new] = new_value
                

    if not changes_made:
        return {"status": "error", "details": "No changes applied"}
    
    db.commit()
    db.refresh(fetched_posts)
    
    return {"status": "success", "details": applied_actions}
        