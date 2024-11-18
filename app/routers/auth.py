from fastapi import HTTPException, status, Depends, APIRouter
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database.connection import get_db
import app.models as models
import app.schemas as schemas
from app.config import settings
from app.utils import email_utils, utils
import app.oauth2 as oauth2
from datetime import datetime, timedelta
import pytz

router = APIRouter(prefix="/auth", tags=['Authentication'])
utc = pytz.UTC

@router.post('/login', response_model=schemas.Token)
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
    
    if not utils.is_password_valid(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials") 
    
    access_token = oauth2.create_access_token(data = {"user_id": user.id})
    
    return {'access_token' : access_token, "token_type": "bearer"}

@router.post('/register', response_model=schemas.GetUsers, status_code=status.HTTP_200_OK)
def register_user(user_credentials: schemas.RegisterUser = Depends(), db: Session = Depends(get_db)):
    
    if utils.is_account_unverified(db, user_credentials.email, user_credentials.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                             detail=schemas.DetailError(type="UnverifiedAccount",
                                                        message="An account with this email or username exists but is not verified.").model_dump())
    
    if email_utils.is_email_valid(user_credentials.email) != user_credentials.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                             detail=schemas.DetailError(type="InvalidEmailFormat",
                                                        message="Invalid email format").model_dump())
    
    if email_utils.is_email_taken(db, user_credentials.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                             detail=schemas.DetailError(type="UserExists",
                                                        message=f"{user_credentials.email} is already taken").model_dump())
    
    if utils.is_username_taken(db, user_credentials.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                             detail=schemas.DetailError(type="UserExists",
                                                        message=f"{user_credentials.username} already registered").model_dump())
    
    password_test = utils.is_password_strength(user_credentials.password)
    if password_test:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                             detail=schemas.DetailError(type="WeakPassword",
                                                        message=f"Weak password: {password_test}").model_dump())
    
    hashed_password = utils.hash_password(user_credentials.password)
    user_credentials.password = hashed_password
    
    code_response = email_utils.send_validation_email(db, user_credentials.email)
    if isinstance(code_response, dict) and not code_response.get("status") == 200:
        raise HTTPException(status_code=code_response.get("status", 500), 
                             detail=schemas.DetailError(type="ValidationEmailError",
                                                        message=code_response.get("message", "Unknown error")).model_dump())
    
    # Create new user
    new_user = models.Users(
        **user_credentials.model_dump(), 
        code=code_response["validation_code"],  # Assuming validation_code is returned
        code_expiration=datetime.now(utc) + timedelta(minutes=float(settings.email_code_expire_minutes)),
        is_validated=False
    )
    
    # Add user to DB and commit
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user
 
@router.post('/verify-code', status_code=status.HTTP_200_OK)
def verify_code(code_validation: schemas.CodeValidation = Depends(), db: Session = Depends(get_db)):
     
     if not utils.is_code_valid(db, code_validation.code):
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                             detail=schemas.DetailError(type="InvalidToken",
                                                        message="Invalid or expired token").model_dump())
     
     user_verified = db.query(models.Users).filter(and_(models.Users.code == code_validation.code, models.Users.is_validated == False)).first()  # noqa: E712
     
     if code_validation.is_password_recovery:
        user_verified.password_recovery = True
     else:
        user_verified.is_validated = True
        
     user_verified.code = None
     user_verified.code_expiration = None
     
     db.commit()
     db.refresh(user_verified)
    
     return {"message": "code verified"}
 
@router.post('/refresh-code', status_code=status.HTTP_200_OK)
def refresh_code(email_refresh: schemas.CodeValidation = Depends(), db: Session = Depends(get_db)):
    
    code_response = email_utils.resend_email(db, email_refresh.code)
    
    if "error" in code_response:
        raise HTTPException(
            status_code=code_response.get("status", 500),
            detail=schemas.DetailError(
                type="ValidationEmailError",
                message=code_response.get("error", "Unknown error")
            ).model_dump()
        )
    
    validation_code = code_response.get("result")
    user_email = code_response.get("user_email")
    
    user = db.query(models.Users).filter(and_(
        models.Users.code == email_refresh.code,
        models.Users.is_validated == False,  # noqa: E712
        models.Users.email == user_email
    )).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                             detail="User not found or already verified")
    
    user.code = validation_code
    user.code_expiration = datetime.now(utc) + timedelta(minutes=float(settings.email_code_expire_minutes))
    
    db.commit()
    db.refresh(user)

    return user

@router.post('/password-recovery', response_model=schemas.GetUsers, status_code=status.HTTP_200_OK)
def password_recovery(user_credentials: schemas.PasswordRecovery = Depends(), db: Session = Depends(get_db)):
    
    code_response = email_utils.send_recovery_email(db, user_credentials.email)
    if isinstance(code_response, dict) and not code_response.get("status") == 200:
        raise HTTPException(status_code=code_response.get("status", 500), 
                             detail=schemas.DetailError(type="ValidationEmailError",
                                                        message=code_response.get("message", "Unknown error")).model_dump())
    
    user_recovery = db.query(models.Users).filter(and_(models.Users.email == user_credentials.email, models.Users.is_validated == True)).first()  # noqa: E712
    
    user_recovery.password_recovery = False
    user_recovery.code_expiration = datetime.now(utc) + timedelta(minutes=float(settings.email_code_expire_minutes))
    
    db.commit()
    db.refresh(user_recovery)
    
    return user_recovery


 
 
         
