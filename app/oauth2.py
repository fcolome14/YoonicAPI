from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
import app.schemas as schemas
from sqlalchemy import and_, or_
from app.config import settings
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from functools import wraps
from sqlalchemy.orm import Session
import app.models as models
from jwt import ExpiredSignatureError, InvalidTokenError, DecodeError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

SECRET_KEY = settings.secret_key
REFRESH_SECRET_KEY = settings.refresh_secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
TYPE= "TokenAuth"


def create_token_wrapper(func):
    @wraps(func)
    def wrapper(data: dict, *args, **kwargs):
        expire = datetime.now(timezone.utc) + timedelta(minutes=kwargs.get("expire_minutes", ACCESS_TOKEN_EXPIRE_MINUTES))
        data["exp"] = expire
        return func(data, *args, **kwargs)
    return wrapper


@create_token_wrapper
def create_access_token(data: dict):
    """Creates an access token."""
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@create_token_wrapper
def create_refresh_token(data: dict):
    """Creates a refresh token."""
    encoded_jwt = jwt.encode(data, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_email_code_token(data: dict):
    expire = datetime.now(timezone.utc) + timedelta(minutes=data.get("expire_minutes", settings.email_code_expire_minutes))
    data["exp"] = expire
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str):
    """Decodes the access token and checks for blacklisting."""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
        detail=schemas.ErrorDetails(
            type=TYPE,
            message="Could not validate credentials",
            details="Expired or missing valid JWT"
        ).model_dump()
    )
    
    # if is_token_blacklisted(db, token):
    #     raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        id: str = payload.get("user_id")
        if id is None:
            raise credentials_exception
        token_data = schemas.TokenData(id=str(id))
    except JWTError:
        raise credentials_exception

    return token_data.id

def decode_email_code_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=schemas.ErrorDetails(
                type=TYPE,
                message="Token has expired",
                details=None
            ).model_dump()
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=schemas.ErrorDetails(
                type=TYPE,
                message="Invalid token",
                details=None
            ).model_dump()
        )
    except DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=schemas.ErrorDetails(
                type=TYPE,
                message="Error decoding token",
                details=None
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=schemas.ErrorDetails(
                type=TYPE,
                message=f"An unexpected error occurred: {str(e)}",
                details=None
            ).model_dump()
        )



def get_user_session(token: str = Depends(oauth2_scheme)):
    """Validates and returns the user session from a token."""
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                             headers={"WWW-Authenticate": "Bearer"},
                             detail=schemas.ErrorDetails(type="Oauth2",
                                                        message="Could not validate access token",
                                                        details=None).model_dump())
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    return payload


def is_token_blacklisted(db: Session, token: str) -> bool:
    """Checks if a token is in the blacklist."""
    return db.query(models.TokenTable).filter(
        and_(models.TokenTable.access_token == token, models.TokenTable.status == False)  # noqa: E712
    ).first() is not None


def invalidate_token(token: schemas.TokenSchema, db: Session):
    """
    Invalidates an access token by setting its status to False in the database.
    
    Args:
        token (str): The token to invalidate.
        db (Session): Database session.
        
    Raises:
        HTTPException: If the token is already invalidated or not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    decode_access_token(token.access_token, credentials_exception, db)
    
    token_entry = db.query(models.TokenTable).filter(
        and_(
            models.TokenTable.access_token == token.access_token,
            models.TokenTable.status == True  # noqa: E712
        )
    ).first()

    if not token_entry:
        raise HTTPException(status_code=404, detail="Token not found or already invalidated")

    # Invalidate the token
    token_entry.status = False
    db.commit()
    db.refresh(token_entry)
    return {"message": "Token invalidated successfully"}