from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TokenSchema(BaseModel):
    access_token:str
    refresh_token:str

class TokenData(BaseModel):
    """ JWT input """
    
    id: Optional[str] = None