from fastapi import FastAPI, Response, HTTPException, status, Depends, APIRouter
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database.connection import get_db
import app.models as models
import app.schemas.token as jwt
import app.utils as utils
import app.oauth2 as oauth2

router = APIRouter(prefix="/login", tags=['Authentication'])

@router.post('/', response_model=jwt.Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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
    
    user = db.query(models.Users).filter(models.Users.username == user_credentials.username).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
    
    if not utils.verify(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials") 
    
    access_token = oauth2.create_access_token(data = {"user_id": user.id})
    
    return {'access_token' : access_token, "token_type": "bearer"}