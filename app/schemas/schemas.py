from pydantic import BaseModel, EmailStr
from typing import Optional, List
from .bases import LoginBase, UsersBase, DetailError

class Login(BaseModel):
    module: str
    functionality: str
    args: LoginBase

class CreateUsers(UsersBase):
    """ Create new user schema """
    password: str

class GetUsers(UsersBase):
    """ Create new user schema """
    #access_token = str
    pass

class GetSIngleUser(BaseModel):
    """ Get single user """
    username: str

class RegisterUser(UsersBase):
    """ Register user """
    password: str

class CodeValidation(BaseModel):
    """ Email code verification """
    code: int
    is_password_recovery: bool

class EmailRefresh(BaseModel):
    """ Refresh email code verification """
    email: EmailStr
    old_code: int

class DetailError(BaseModel):
    """ Detail fail """
    type: str
    message: str

class PasswordChange(LoginBase):
    new_password: str
    
class PasswordRecovery(BaseModel):
    email: EmailStr

    
