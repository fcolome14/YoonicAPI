from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Users
from app.utils import utils, time_utils
import random
from string import digits

from app.responses import SystemResponse
from app.schemas.schemas import ResponseStatus, RegisterInput
import inspect

class AuthService:
    
    @staticmethod
    def validate_user(db: Session, username: str):
        user =  (
        db.query(Users)
        .filter(
            and_(
                Users.username == username,
                Users.is_validated == True, # noqa: E712
            )
        )
        .first()
    )
        status=ResponseStatus.ERROR
        message="User not found"
        origin = inspect.stack()[0].function
        if user:
            status=ResponseStatus.SUCCESS
            message=user

        return SystemResponse.internal_response(
            status, origin, message)
    
    @staticmethod
    def validate_register(db:Session, user_credentials: RegisterInput):
        origin = inspect.stack()[0].function
        
        result = utils.is_account_unverified(
        db, user_credentials.email, user_credentials.username)
        if result.status == ResponseStatus.ERROR:
            return SystemResponse.internal_response(
                ResponseStatus.ERROR,
                origin,
                "Account already registered")
        
        result = utils.is_username_email_taken(
        db=db, username=user_credentials.username, email=user_credentials.email)
        if result.status == ResponseStatus.ERROR:
            return SystemResponse.internal_response(
                ResponseStatus.ERROR,
                origin,
                "Username or Email already exists")
        
        result = utils.is_password_strong(user_credentials.password)
        if result.status == ResponseStatus.ERROR:
            return SystemResponse.internal_response(
                ResponseStatus.ERROR,
                origin,
                "Weak password")
        
        return SystemResponse.internal_response(
            ResponseStatus.SUCCESS,
            origin,
            "All checks passed"
        )
        
    def add_user(db: Session, code: int, user_credentials: RegisterInput):
        origin = inspect.stack()[0].function
        result = AuthService._create_user(user_credentials, code)
        if result.status == ResponseStatus.ERROR:
            return SystemResponse.internal_response(
            ResponseStatus.ERROR,
            result.origin,
            result.message)
        
        result = AuthService._add_user(db, result.message)
        if result.status == ResponseStatus.ERROR:
            return SystemResponse.internal_response(
            ResponseStatus.ERROR,
            result.origin,
            result.message)
        
        return SystemResponse.internal_response(
            ResponseStatus.SUCCESS,
            origin,
            "User added to database")
    
    def _create_user(user_credentials: RegisterInput, code: int):
        origin = inspect.stack()[0].function
        status = ResponseStatus.SUCCESS
        try:
            message = Users(
            **user_credentials.model_dump(),
            code=int(code),
            code_expiration=time_utils.compute_expiration_time(),
            is_validated=False)
        except Exception as exc:
            status = ResponseStatus.ERROR
            message = f"Error raised from database: {exc}"
        
        return SystemResponse.internal_response(status, origin, message)
    
    def _add_user(db: Session, new_user: Users):
        message = ""
        origin = inspect.stack()[0].function
        status = ResponseStatus.SUCCESS
        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
        except Exception as exc:
            status = ResponseStatus.ERROR
            message = f"Error raised from database: {exc}"
            
        return SystemResponse.internal_response(status, origin, message)
    
    @staticmethod
    def generate_code(db: Session) -> int:
        """Generates unique random code

        Args:
            db (Session): Database connection

        Returns:
            int: Code
        """
        origin = inspect.stack()[0].function
        status = ResponseStatus.SUCCESS
        
        while True:
            validation_code = ""
            validation_code = "".join(random.choices(digits, k=6))
            if (
                not db.query(Users)
                .filter(and_(Users.code == validation_code))
                .first()
            ):  # noqa: E712
                break

        return SystemResponse.internal_response(status, origin, validation_code)