from fastapi import Depends, APIRouter, status, HTTPException, Request
from sqlalchemy.orm import Session
from app.database.connection import get_db
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
import app.models as models
from sqlalchemy import or_, and_
import app.schemas as schemas
from app.utils import email_utils, utils
from typing import Annotated
from app.config import get_firebase_user_from_token


router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{username}", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse)
def get_users(username: str, db: Session=Depends(get_db)):
    """Get user data

    Args:
        username (str): User's username
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Raises:
        HTTPException: If user not found

    Returns:
        _type_: User data
    """
    
    users = db.query(models.Users).filter(models.Users.username == username).first()
    
    if not users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {username} not found")
    
    return users


@router.get("/userid")
async def get_userid(user: Annotated[dict, Depends(get_firebase_user_from_token)]):
    """gets the firebase connected user"""
    return {"id": user["uid"]}


@router.post("/change_password", status_code=status.HTTP_201_CREATED, response_model=schemas.SuccessResponse)
def password_change(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session=Depends(get_db), request: Request = None):
    
    
    user = db.query(models.Users).filter(and_(models.Users.username == user_credentials.username,  
                                               models.Users.is_validated == True)).first() # noqa: E712
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                             detail=schemas.ErrorDetails(type="PasswordChange",
                                                        message="No user found",
                                                        details=None).model_dump())
    
    if utils.is_password_valid(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                             detail=schemas.ErrorDetails(type="PasswordChange",
                                                        message="New password must be different from old one",
                                                        details=None).model_dump())
    
    if not utils.is_password_strong(user_credentials.password):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                             detail=schemas.ErrorDetails(type="PasswordChange",
                                                        message="Weak password",
                                                        details=None).model_dump())
    
    user.password = utils.hash_password(user_credentials.password)
    
    db.commit()
    db.refresh(user)
    
    return schemas.SuccessResponse(
        status="success",
        message="Password changed",
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )
