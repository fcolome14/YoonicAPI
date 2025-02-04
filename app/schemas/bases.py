from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, Field, field_validator


class Context(BaseModel):
    request_id: Optional[str] = None
    client: Optional[str] = Field(
        default="unknown", description="Client type (e.g., web, mobile)"
    )
    version: Optional[str] = Field(default="1.0.0", description="API version")


class BaseInput(BaseModel):
    context: Optional[Context] = None
    payload: Any

    @field_validator("payload")
    def payload_must_not_be_empty(cls, value):
        if not value:
            raise ValueError("Payload cannot be empty")
        return value


class MetaData(BaseModel):

    request_id: Optional[str] = None
    client: Optional[str] = None

class ErrorDetails(BaseModel):

    type: str
    message: str
    details: Optional[str] = None


class ErrorDetailsHandler(BaseModel):

    type: str
    details: Optional[str] = None


class RateDetails(BaseModel):

    title: str
    amount: float
    currency: str


class EventLines(BaseModel):

    start: datetime
    end: datetime
    rate: Union[RateDetails, List[RateDetails]]
    isPublic: bool
    capacity: Optional[int] = 0
    invited: Optional[List[int]] = None


class UpdateDetails(BaseModel):

    field: str
    value: Any


class UpdateChanges(BaseModel):

    id: int
    update: Optional[List[UpdateDetails]] = None

class UpdateConfirmChanges(BaseModel):

    status: str
    source: str
    message: Union[str, None]
    header_id: int
    record_id: int
    field: str
    old_value: Any
    new_value: Any

class Deletes(BaseModel):

    id: int


class TableChanges(BaseModel):
    
    table: int
    changes: List[UpdateChanges]
