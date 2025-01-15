from typing import Annotated
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.schemas.schemas import ResponseStatus, InternalResponse, SuccessResponse
from app.responses import SuccessHTTPResponse, ErrorHTTPResponse

from app.services.user_service import UserService
from app.models import Users
from app.config import get_firebase_user_from_token
from app.database.connection import get_db
from app.utils import email_utils, utils

router = APIRouter(prefix="/users", tags=["Users"])
class UsersTypes(Enum):
    PWD_RECOV = "Password Recovery"


@router.put(
    "/change-password",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse,
)
def password_change(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None,
):

    result: InternalResponse = UserService.validate_password_recovery(
        db,
        user_credentials.username,
        user_credentials.password)
    
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            UsersTypes.PWD_RECOV, 
            status.HTTP_404_NOT_FOUND,
            message=result.message,
            details="User not found")
    
    return SuccessHTTPResponse.success_response(
        UsersTypes.PWD_RECOV, 
        result.message, 
        request)