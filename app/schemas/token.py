from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    """ JWT returned after succeed login """
    
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """ JWT input """
    
    id: Optional[str] = None