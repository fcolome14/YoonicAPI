from pydantic import BaseModel
from .bases import LoginBase, UsersBase

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