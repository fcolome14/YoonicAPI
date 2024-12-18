from datetime import datetime, timedelta, timezone

import pytz
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_
from sqlalchemy.orm import Session

import app.models as models
import app.oauth2 as oauth2
import app.schemas as schemas
from app.config import settings
from app.database.connection import get_db
from app.utils import email_utils, utils

router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="app/templates")
utc = pytz.UTC


@router.post(
    "/login",
    response_model=schemas.SuccessResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """User login authentication

    Args:
        user_credentials (OAuth2PasswordRequestForm, optional): User credentials stored inside a secured object. Defaults to Depends().
        db (Session, optional): Database connection instance. Defaults to Depends(get_db).

    Raises:
        HTTPException: User not found
        HTTPException: Invalid credentials

    Returns:
        _type_: Session JWT
    """

    user = (
        db.query(models.Users)
        .filter(
            and_(
                models.Users.username == user_credentials.username,
                models.Users.is_validated == True,
            )
        )
        .first()
    )  # noqa: E712

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=schemas.ErrorDetails(
                type="Auth", message="Invalid Credentials", details="User not found"
            ).model_dump(),
        )

    # if utils.is_user_logged(db, user_credentials.username):
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
    #                          detail=schemas.ErrorDetails(type="Auth",
    #                                                     message="User already logged in",
    #                                                     details=None).model_dump())

    if not utils.is_password_valid(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=schemas.ErrorDetails(
                type="Auth", message="Invalid Credentials", details="Invalid password"
            ).model_dump(),
        )

    access_token = oauth2.create_access_token(data={"user_id": user.id})
    refresh_token = oauth2.create_refresh_token(data={"user_id": user.id})

    token_db = models.TokenTable(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        status=True,
    )

    db.add(token_db)
    db.commit()
    db.refresh(token_db)

    return schemas.SuccessResponse(
        status="success",
        message="Login succeed",
        data={
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "token": access_token,
        },
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )


@router.post(
    "/logout", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse
)
def logout(
    token: str = Depends(oauth2.oauth2_scheme),
    db: Session = Depends(get_db),
    _: int = Depends(oauth2.get_user_session),
    request: Request = None,
) -> schemas.SuccessResponse:
    """Logout endpoint to invalidate an access token

    Args:
        token (str, optional): Access token from the Authorization header. Defaults to Depends(oauth2.oauth2_scheme).
        db (Session, optional): Database session. Defaults to Depends(get_db).
        _ (int, optional): User Id. Defaults to Depends(oauth2.get_user_session).
        request (Request, optional): Header. Defaults to None.

    Raises:
        HTTPException: When an error occurs

    Returns:
        schemas.SuccessResponse: Succesful JSON
    """

    token_entry = (
        db.query(models.TokenTable)
        .filter(
            and_(
                models.TokenTable.access_token == token,
                models.TokenTable.status == True,  # noqa: E712
            )
        )
        .first()
    )

    if not token_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=schemas.ErrorDetails(
                type="Logout", message="Token not found or invalidated", details=None
            ).model_dump(),
        )

    db.delete(token_entry)
    db.commit()

    return schemas.SuccessResponse(
        status="success",
        message="Logout",
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )


@router.post(
    "/register", response_model=schemas.SuccessResponse, status_code=status.HTTP_200_OK
)
def register_user(
    user_credentials: schemas.RegisterInput,
    db: Session = Depends(get_db),
    request: Request = None,
):

    if utils.is_account_unverified(
        db, user_credentials.email, user_credentials.username
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=schemas.ErrorDetails(
                type="Register",
                message="Unverified account",
                details=f"An account with '{user_credentials.email}' or '{user_credentials.username}' exists but is not verified yet",
            ).model_dump(),
        )

    if utils.is_username_email_taken(
        db=db, username=user_credentials.username, email=user_credentials.email
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=schemas.ErrorDetails(
                type="Register",
                message="Username or Email already exists",
                details=f"Username '{user_credentials.username}' or '{user_credentials.email}' is already taken",
            ).model_dump(),
        )

    password_test = utils.is_password_strong(user_credentials.password)
    if not password_test:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=schemas.ErrorDetails(
                type="Register", message="Weak password", details=None
            ).model_dump(),
        )

    hashed_password = utils.hash_password(user_credentials.password)
    user_credentials.password = hashed_password

    code_response = email_utils.send_auth_code(db, user_credentials.email)
    if code_response.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=schemas.ErrorDetails(
                type="Register",
                message=code_response.get("message"),
                details="Sending validation email",
            ).model_dump(),
        )

    new_user = models.Users(
        **user_credentials.model_dump(),
        code=code_response.get("message"),
        code_expiration=datetime.now(timezone.utc).replace(tzinfo=pytz.utc)
        + timedelta(minutes=settings.email_code_expire_minutes),
        is_validated=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return schemas.SuccessResponse(
        status="success",
        message="Account pending validation",
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )


@router.get("/verify-code", status_code=status.HTTP_200_OK)
def verify_code(
    token: str, db: Session = Depends(get_db), request: Request = None
) -> schemas.SuccessResponse:
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
            detail=schemas.ErrorDetails(
                type="VerifyCode", message=decoded_token.get("message"), details=None
            ).model_dump(),
        )
    email = decoded_token.get("email")
    code = decoded_token.get("code")

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

    user_verified = db.query(models.Users).filter(models.Users.code == code).first()
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
    response_model=schemas.SuccessResponse,
    status_code=status.HTTP_200_OK,
)
def refresh_code(
    email_refresh: schemas.CodeValidationInput,
    db: Session = Depends(get_db),
    request: Request = None,
) -> schemas.SuccessResponse:
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
            detail=schemas.ErrorDetails(
                type="RefreshCode",
                message="Previous requested code is still active",
                details=None,
            ).model_dump(),
        )

    code_response = email_utils.resend_auth_code(db, email_refresh.code)

    if code_response.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=schemas.ErrorDetails(
                type="RefreshCode", message=code_response.get("message"), details=None
            ).model_dump(),
        )

    user: models.Users = code_response.get("user")

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=schemas.ErrorDetails(
                type="RefreshCode", message="User not found", details=None
            ).model_dump(),
        )

    user.code = code_response.get("new_code")
    user.code_expiration = datetime.now(utc) + timedelta(
        minutes=settings.email_code_expire_minutes
    )

    db.commit()
    db.refresh(user)

    return schemas.SuccessResponse(
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
    response_model=schemas.SuccessResponse,
    status_code=status.HTTP_200_OK,
)
def password_recovery_code(
    user_credentials: schemas.RecoveryCodeInput,
    db: Session = Depends(get_db),
    request: Request = None,
) -> schemas.SuccessResponse:
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
        not db.query(models.Users)
        .filter(
            and_(
                models.Users.email == user_credentials.email,
                models.Users.is_validated == True,
            )
        )
        .first()
    ):  # noqa: E712
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=schemas.ErrorDetails(
                type="RecoveryCode", message="User not found", details=None
            ).model_dump(),
        )

    code_response = email_utils.send_auth_code(db, user_credentials.email, 1)
    if code_response.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=schemas.ErrorDetails(
                type="RecoveryCode",
                message=code_response.get("message"),
                details="Sending validation email for password recovery code",
            ).model_dump(),
        )

    user_recovery = (
        db.query(models.Users)
        .filter(
            and_(
                models.Users.email == user_credentials.email,
                models.Users.is_validated == True,
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

    return schemas.SuccessResponse(
        status="success",
        message="Account recovery validation sent",
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )
