from pydantic import BaseModel, EmailStr
from typing import Optional, Any
from .bases import MetaData, ErrorDetails


#OUTPUTS
class SuccessResponse(BaseModel):
    
    status: str
    message: str
    data: Optional[Any] = None
    meta: Optional[MetaData] = None

class ErrorResponse(BaseModel):
    
    status: str
    message: str
    data: ErrorDetails
    meta: Optional[MetaData] = None
    
    
#REGISTER
class RegisterInput(BaseModel):
    
    email: EmailStr
    password: str
    full_name: str
    username: str

#CODE VALIDATION
class CodeValidationInput(BaseModel):
    """ Email code verification """
    code: int
    email: EmailStr

class RecoveryCodeInput(BaseModel):
    """ Email code verification """
    email: EmailStr


    
