from fastapi import Depends, APIRouter, status, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
import app.models as models
import app.schemas as schemas
import app.utils as utils

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