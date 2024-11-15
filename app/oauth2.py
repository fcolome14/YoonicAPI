from jose import JWTError, jwt
from datetime import datetime, timedelta
import app.schemas.bases as bases
from app.database.config import settings
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

def create_access_token(data: dict):
    """Returns access token based on the input args

    Args:
        data (dict): Input dictionary format data

    Returns:
        _type_: JWT object
    """
    to_encode = data.copy()
    
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) #Header, Payload, Signature
    
    return encoded_jwt

def decode_access_token(token: str, credentials_exception):
    """Returns decoded JWT data content

    Args:
        token (str): Session access token
        credentials_exception (_type_): Exception

    Raises:
        credentials_exception: If user not found
        credentials_exception: If invalid JWT

    Returns:
        _type_: _description_
    """
    
    try:
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        id: str = payload.get("user_id") #Gets the dict key from the decoded payload from auth.py and stores it in id var
        
        if id is None:
            raise credentials_exception
        token_data = bases.TokenData(id=str(id)) #Sets the recovered id to the TokenData schema
    
    except JWTError:
        raise credentials_exception
    
    return token_data

def get_current_user(token: str = Depends(oauth2_scheme)):
    """Returns user's session JWT

    Args:
        token (str, optional): Encoded JWT. Defaults to Depends(oauth2_scheme).

    Returns:
        _type_: User JWT data content
    """
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                                          detail="Could not validate credentials",
                                          headers={"WWW-Authenticate": "Bearer"})
    
    return decode_access_token(token, credentials_exception)