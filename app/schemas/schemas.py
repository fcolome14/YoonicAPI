from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, List, Union, Tuple
from .bases import MetaData, ErrorDetails, EventLines, TableChanges
from datetime import datetime


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
    location: Union[str, Tuple[float, float]] #Allow address "str" or coordinates [x, y]
    category: int
    user_timezone: str
    line: Optional[Union[EventLines, List[EventLines]]] = None
    repeat: bool
    custom_option_selected: bool
    when_to: Optional[int] = None #Possible values: 0, 1, 2, 3 (or 4) if custom_selected = true
    occurrences: Optional[int] = None
    for_days: Optional[Tuple[int, ...]] = Field(
        None,
        description="Optional array of days (0-6, where 0=Monday, 6=Sunday) to repeat the event."
    )
    custom_each_day: Optional[bool] = None
    until_to: Optional[Union[int, Tuple[int, Union[datetime, int]]]] = None
    custom_lines: Optional[List[EventLines]] = None
    

class UpdatePostInput(BaseModel):
    """ Update post """
    tables: List[TableChanges]
    

    
