from pydantic import BaseModel, EmailStr
from typing import Optional, Any, List, Union, Tuple
from .bases import MetaData, ErrorDetails
from datetime import datetime
from decimal import Decimal
from enum import Enum


#OUTPUTS
class SuccessResponse(BaseModel):
    """ Common success request response body """
    status: str = "success"
    message: str
    data: Optional[Any] = None
    meta: Optional[MetaData] = None

class ErrorResponse(BaseModel):
    """ Common failed request response body """
    status: str = "error"
    message: str
    data: ErrorDetails
    meta: Optional[MetaData] = None
    
    
#REGISTER
class RegisterInput(BaseModel):
    """ Register new user input """
    email: EmailStr
    password: str
    full_name: str
    username: str

#CODE VALIDATION
class CodeValidationInput(BaseModel):
    """ Verification email code """
    code: int
    email: EmailStr

class RecoveryCodeInput(BaseModel):
    """ Email code verification """
    email: EmailStr

#POSTS
class NewPostInput(BaseModel):
    """ New posts """
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    location: Union[str, Tuple[float, float]] #Allow address or coordinates
    isPublic: bool
    category: int
    owner_id: int
    # tags: Optional[List[str]] = None
    cost: Optional[Decimal] = 0
    currency: Optional[Enum] = None
    capacity: Optional[int] = None
    

    
