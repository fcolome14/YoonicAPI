from datetime import datetime, timedelta, timezone
from enum import Enum

import pytz
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models import Users, TokenTable
import app.oauth2 as oauth2
from app.schemas.schemas import (ResponseStatus, 
                                 SuccessResponse, 
                                 RegisterInput,
                                 ErrorDetails, 
                                 CodeValidationInput,
                                 RecoveryCodeInput)
from app.config import settings
from app.database.connection import get_db
from app.utils import email_utils, utils
from app.responses import ErrorHTTPResponse, SuccessHTTPResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="app/templates")
utc = pytz.UTC

class AuthTypes(Enum):
    LOGIN = "Login"
    LOGOUT = "Login"
    CODE = "ValidationCode"
    REGISTER = "Register"


@router.post(
    "/login",
    response_model=SuccessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    User login authentication

    Args:
        user_credentials (OAuth2PasswordRequestForm, optional): User credentials stored inside a secured object. Defaults to Depends().
        db (Session, optional): Database connection instance. Defaults to Depends(get_db).

    Raises:
        HTTPException: User not found
        HTTPException: Invalid credentials

    Returns:
        _type_: Session JWT
    """

    result = AuthService.validate_user(db, user_credentials.username)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            AuthTypes.LOGIN, 
            status.HTTP_404_NOT_FOUND,
            message="Invalid Credentials",
            details="User not found")
    
    user: Users = result.message
    if not utils.is_password_valid(user_credentials.password, user.password):
        raise ErrorHTTPResponse.error_response(
            AuthTypes.LOGIN, 
            status.HTTP_401_UNAUTHORIZED,
            message="Invalid Credentials",
            details="Invalid password")
        
    access_token = oauth2.create_access_token(data={"user_id": user.id})
    return SuccessHTTPResponse.success_response(
        message="Login succeed",
        attatched_data={
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "token": access_token,
        },
        request=request
    )

@router.post(
    "/logout", status_code=status.HTTP_200_OK, response_model=SuccessResponse
)
def logout(
    token: str = Depends(oauth2.oauth2_scheme),
    db: Session = Depends(get_db),
    _: int = Depends(oauth2.get_user_session),
    request: Request = None,
) -> SuccessResponse:
    """Logout endpoint to invalidate an access token

    Args:
        token (str, optional): Access token from the Authorization header. Defaults to Depends(oauth2.oauth2_scheme).
        db (Session, optional): Database session. Defaults to Depends(get_db).
        _ (int, optional): User Id. Defaults to Depends(oauth2.get_user_session).
        request (Request, optional): Header. Defaults to None.

    Raises:
        HTTPException: When an error occurs

    Returns:
        schemas.SuccessResponse: Success JSON
    """

    # token_entry = (
    #     db.query(TokenTable)
    #     .filter(
    #         and_(
    #             TokenTable.access_token == token,
    #             TokenTable.status == True,  # noqa: E712
    #         )
    #     )
    #     .first()
    # )

    # if not token_entry:
    #     raise ErrorHTTPResponse.error_response(
    #         AuthTypes.LOGOUT, 
    #         status.
    #         message="Invalid Credentials",
    #         details="User not found")
        
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=ErrorDetails(
    #             type="Logout", message="Token not found or invalidated", details=None
    #         ).model_dump(),
    #     )

    # db.delete(token_entry)
    # db.commit()

    return SuccessResponse(
        status="success",
        message="Logout",
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )


@router.post(
    "/register", response_model=SuccessResponse, status_code=status.HTTP_200_OK
)
def register_user(
    user_credentials: RegisterInput,
    db: Session = Depends(get_db),
    request: Request = None,
):
    result = AuthService.validate_register(db, user_credentials)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            AuthTypes.REGISTER, 
            status.HTTP_409_CONFLICT,
            message=result.message,
            details=None) 
        
    result = utils.hash_password(user_credentials.password)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            AuthTypes.REGISTER, 
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=result.message,
            details=None)  
    user_credentials.password = result.message

    code_response = email_utils.send_auth_code(db, user_credentials.email)
    if code_response.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            AuthTypes.REGISTER, 
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=result.message,
            details=None) 
        
    result = AuthService.add_user(db, code_response.message, user_credentials)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            AuthTypes.REGISTER, 
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=result.message,
            details=None) 

    return SuccessHTTPResponse.success_response(
        message="Account pending of validation",
        attatched_data={},
        request=request
    )


@router.get("/verify-code", status_code=status.HTTP_200_OK)
def verify_code(
    token: str, db: Session = Depends(get_db), request: Request = None
) -> SuccessResponse:
    """Validation of provided code

    Args:
        token (str): _description_
        db (Session, optional): _description_. Defaults to Depends(get_db).
        request (Request, optional): _description_. Defaults to None.

    Raises:
        HTTPException: _description_

    Returns:
        schemas.SuccessResponse: _description_
    """

    decoded_token = oauth2.decode_email_code_token(token)
    if decoded_token.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorDetails(
                type="VerifyCode", message=decoded_token.get("message"), details=None
            ).model_dump(),
        )
        
    email, code = decoded_token["email"], decoded_token["code"]
    response = utils.is_code_valid(db, code, email)
    if response.get("status") == "error":
        message = response.get("details", "An error occurred during verification.")
        return templates.TemplateResponse(
            "code_verification_result.html",
            {
                "request": request,
                "message": message,
                "email": None,
                "success": False,
            },
        )

    user_verified = db.query(Users).filter(Users.code == code).first()
    if not user_verified:
        message = "The user associated with this code was not found."
        return templates.TemplateResponse(
            "code_verification_result.html",
            {
                "request": request,
                "message": message,
                "email": None,
                "success": False,
            },
        )

    user_verified.is_validated = True
    user_verified.code = None
    user_verified.code_expiration = None

    db.commit()
    db.refresh(user_verified)

    message = response.get("details", "Your verification was successful!")
    return templates.TemplateResponse(
        "code_verification_result.html",
        {
            "request": request,
            "message": message,
            "email": settings.email,
            "success": True,
        },
    )


@router.post(
    "/refresh-code",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
def refresh_code(
    email_refresh: CodeValidationInput,
    db: Session = Depends(get_db),
    request: Request = None,
) -> SuccessResponse:
    """Refresh the validation code by sending a new email

    Args:
        email_refresh (schemas.CodeValidationInput): _description_
        db (Session, optional): _description_. Defaults to Depends(get_db).
        request (Request, optional): _description_. Defaults to None.

    Raises:
        HTTPException: _description_
        HTTPException: _description_
        HTTPException: _description_

    Returns:
        schemas.SuccessResponse: _description_
    """

    if utils.is_code_expired(db=db, email=email_refresh.email, code=email_refresh.code):
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=ErrorDetails(
                type="RefreshCode",
                message="Previous requested code is still active",
                details=None,
            ).model_dump(),
        )

    code_response = email_utils.resend_auth_code(db, email_refresh.code)

    if code_response.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorDetails(
                type="RefreshCode", message=code_response.get("message"), details=None
            ).model_dump(),
        )

    user: Users = code_response.get("user")

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetails(
                type="RefreshCode", message="User not found", details=None
            ).model_dump(),
        )

    user.code = code_response.get("new_code")
    user.code_expiration = datetime.now(utc) + timedelta(
        minutes=settings.email_code_expire_minutes
    )

    db.commit()
    db.refresh(user)

    return SuccessResponse(
        status="success",
        message="CodeRefresh",
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )


@router.post(
    "/recovery-code",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
)
def password_recovery_code(
    user_credentials: RecoveryCodeInput,
    db: Session = Depends(get_db),
    request: Request = None,
) -> SuccessResponse:
    """Send a new email validation code using a 'recovery' HTML template

    Args:
        user_credentials (schemas.RecoveryCodeInput): _description_
        db (Session, optional): _description_. Defaults to Depends(get_db).
        request (Request, optional): _description_. Defaults to None.

    Raises:
        HTTPException: _description_
        HTTPException: _description_

    Returns:
        schemas.SuccessResponse: _description_
    """

    if (
        not db.query(Users)
        .filter(
            and_(
                Users.email == user_credentials.email,
                Users.is_validated == True,
            )
        )
        .first()
    ):  # noqa: E712
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetails(
                type="RecoveryCode", message="User not found", details=None
            ).model_dump(),
        )

    code_response = email_utils.send_auth_code(db, user_credentials.email, 1)
    if code_response.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorDetails(
                type="RecoveryCode",
                message=code_response.get("message"),
                details="Sending validation email for password recovery code",
            ).model_dump(),
        )

    user_recovery = (
        db.query(Users)
        .filter(
            and_(
                Users.email == user_credentials.email,
                Users.is_validated == True,
            )
        )
        .first()
    )  # noqa: E712

    user_recovery.code = code_response.get("message")
    user_recovery.code_expiration = datetime.now(utc) + timedelta(
        minutes=settings.email_code_expire_minutes
    )

    db.commit()
    db.refresh(user_recovery)

    return SuccessResponse(
        status="success",
        message="Account recovery validation sent",
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )
