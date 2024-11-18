from fastapi import Depends, APIRouter, status, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
import app.models as models
from sqlalchemy import or_, and_
import app.schemas as schemas
from app.utils import email_utils, utils

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.GetUsers)
def create_users(users: schemas.CreateUsers, db: Session=Depends(get_db)):
    """Create new user

    Args:
        users (schemas.CreateUsers): Input schema
        db (Session, optional): Database session. Defaults to Depends(get_db).

    Returns:
        _type_: User data
    """
    
    hashed_pwd = utils.hash(users.password)
    users.password = hashed_pwd
    
    new_user = models.Users(**users.model_dump())
    db.add(new_user)
    db.commit()
    
    return new_user


@router.get("/{username}", status_code=status.HTTP_200_OK, response_model=schemas.GetUsers)
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

@router.post("/password_change", status_code=status.HTTP_201_CREATED, response_model=schemas.GetUsers)
def password_change(users_credentials: schemas.PasswordChange, db: Session=Depends(get_db)):
    
    user = db.query(models.Users).filter(and_(models.Users.email == users_credentials.email,  
                                               models.Users.is_validated == True)).first() # noqa: E712
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active user not found") 
    
    if not utils.is_password_valid(users_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials") 
    
    password_test = utils.is_password_strong(users_credentials.new_password)
    if password_test:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                             detail=schemas.DetailError(type="WeakPassword",
                                                        message=f"Weak password: {password_test}").model_dump())
        
    if utils.is_user_valid(db, users_credentials.email, users_credentials.password):
        user.password = utils.hash_password(users_credentials.new_password)
        db.commit()
        db.refresh(user)
        return user
    
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
