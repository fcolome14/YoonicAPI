from enum import Enum

from app.schemas.schemas import ResponseStatus

import pytz
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
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
from app.utils import email_utils, utils, fetch_data_utils
from app.responses import ErrorHTTPResponse, SuccessHTTPResponse, InternalResponse
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

    result = AuthService.validate_user(db, 
                                       user_credentials.username, 
                                       user_credentials.password)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            AuthTypes.LOGIN, 
            status.HTTP_404_NOT_FOUND,
            message="Invalid Credentials",
            details="User not found")
    
    user: Users = result.message
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
    result: InternalResponse = AuthService.validate_register(db, user_credentials)
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
        token (str): Received JWT
        db (Session, optional): Connection session. Defaults to Depends(get_db).
        request (Request, optional): Request metadata. Defaults to None.

    Raises:
        HTTPException: Found errors while validating code

    Returns:
        schemas.SuccessResponse: Validating code succeed
    """

    result: InternalResponse = oauth2.decode_email_code_token(token)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            AuthTypes.REGISTER, 
            status.HTTP_401_UNAUTHORIZED,
            message=result.message,
            details=None)
        
    email, code = result.message["email"], result.message["code"]
    result = fetch_data_utils.validate_code(db, code, email)
    if result.status == ResponseStatus.ERROR:
        message = "An error occurred during verification."
        return templates.TemplateResponse(
            "code_verification_result.html",
            {
                "request": request,
                "message": message,
                "email": None,
                "success": False,
            },
        )

    user: Users = result.message
    if not user:
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

    result = fetch_data_utils.add_user(db, user)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            AuthTypes.REGISTER, 
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=result.message,
            details=None)
        
    message = "Your verification was successful!"
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
    result: InternalResponse = fetch_data_utils.validate_code(db, email_refresh.code, email_refresh.email)
    if result.status == ResponseStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=ErrorDetails(
                type="RefreshCode",
                message="Previous requested code is still active",
                details=None,
            ).model_dump(),
        )
    if result.status == ResponseStatus.ERROR and result.origin != "is_date_expired":
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=ErrorDetails(
                type="RefreshCode",
                message=result.message,
                details=None,
            ).model_dump(),
        )
        
    result = email_utils.resend_auth_code(db, email_refresh.code)
    if result.status == ResponseStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=ErrorDetails(
                type="RefreshCode",
                message=result.message[0],
                details=None,
            ).model_dump(),
        )

    code, user = result.message
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetails(
                type="RefreshCode", 
                message="User not found", 
                details=None
            ).model_dump(),
        )

    result = fetch_data_utils.refresh_code(db, code, user.email, user.username)
    if result.status == ResponseStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetails(
                type="RefreshCode", 
                message=result.message, 
                details=None
            ).model_dump(),
        )
    
    return SuccessHTTPResponse.success_response(
        message="New validation code was sent via email",
        attatched_data={},
        request=request
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

    result: InternalResponse = fetch_data_utils.validate_email(db, user_credentials.email)
    if result.status == ResponseStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetails(
                type="RecoveryCode", 
                message=result.message, 
                details=None
            ).model_dump(),
        )
    user: Users = result.message
    
    result = email_utils.send_auth_code(db, user_credentials.email, 1)
    if result.status == ResponseStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetails(
                type="RecoveryCode", 
                message=result.message, 
                details="Sending validation email for password recovery code"
            ).model_dump(),
        )

    code = result.message
    result = fetch_data_utils.refresh_code(db, code, user.email, user.username, True)
    if result.status == ResponseStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorDetails(
                type="RefreshCode", 
                message=result.message, 
                details=None
            ).model_dump(),
        )
    
    return SuccessHTTPResponse.success_response(
        message="New validation code was sent via email",
        attatched_data={},
        request=request
    )
