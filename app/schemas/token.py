from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenData(BaseModel):
    """JWT input"""

    id: Optional[str] = None
