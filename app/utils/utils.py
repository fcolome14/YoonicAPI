from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import app.models as models
import pytz
from datetime import datetime
import random
import string

utc = pytz.UTC

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(pwd: str):
    return pwd_context.hash(pwd)

def is_password_valid(plain_password: str, hash_password: str) -> bool:
    return pwd_context.verify(plain_password, hash_password)

def is_user_valid(db: Session, email: str, password: str) -> models.Users | None:
    user = db.query(models.Users).filter(and_(models.Users.email == email,  
                                               models.Users.is_validated == True))  # noqa: E712
    if user:
        return True
    
    return False

def is_password_strong(plain_password: str) -> bool:
    if len(plain_password) < 8:
        return False
    if not any(char.isdigit() for char in plain_password):
        return False
    if not any(char.isalpha() for char in plain_password):
        return False 
    return True 

def is_username_taken(db: Session, username: str):
    return db.query(models.Users).filter(and_(models.Users.username == username, models.Users.is_validated == True)).first()  # noqa: E712

def is_account_unverified(db: Session, email: str, username: str):
    return db.query(models.Users).filter(and_(models.Users.email == email, models.Users.is_validated == False, models.Users.username == username)).first()  # noqa: E712

def is_code_valid(db: Session, code: int) -> bool:
    
    fetched_record = db.query(models.Users).filter(models.Users.code == code).first()  # noqa: E712
    
    if not fetched_record or not fetched_record.code_expiration:
        return False
    if fetched_record.code_expiration < datetime.utcnow().replace(tzinfo=utc):
        return False
    
    return True

def generate_code(db: Session):
    while True:
        validation_code = ""
        validation_code = ''.join(random.choices(string.digits, k=6))
        if not db.query(models.Users).filter(and_(models.Users.code == validation_code, models.Users.is_validated == False)).first():  # noqa: E712
            break
        
    return validation_code