from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class LoginBase(BaseModel):
    """ Base for login """
    
    email: EmailStr
    password: str
    
class UsersBase(BaseModel):
    """ Base for users """
    
    username: str
    email: EmailStr
    full_name: str
    
class DetailError(BaseModel):
    
    code: str
    message: str