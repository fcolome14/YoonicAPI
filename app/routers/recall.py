import pytz
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from enum import Enum

import app.models as models
from app.database.connection import get_db
from app.oauth2 import get_user_session
from app.rate_limit import limiter
from app.schemas import schemas
from app.utils import maps_utils, fetch_data_utils

from app.schemas.schemas import ResponseStatus, InternalResponse, SuccessResponse
from app.responses import SuccessHTTPResponse, ErrorHTTPResponse

router = APIRouter(prefix="/recall", tags=["Configuration recall"])
utc = pytz.UTC
class UsersTypes(Enum):
    CAT = "Categories Settings"
    TAGS = "Tags Settings"

@router.get(
    "/categories",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
def get_categories(
    db: Session = Depends(get_db),
    _: int = Depends(get_user_session),
    request: Request = None,
) -> schemas.SuccessResponse:
    
    result: InternalResponse = fetch_data_utils.get_categories(db)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            UsersTypes.CAT, 
            status.HTTP_404_NOT_FOUND,
            message=result.message,
            details="User not found")
    
    categories = result.message
    return SuccessHTTPResponse.success_response(
        UsersTypes.CAT, 
        categories, 
        request)


@router.get(
    "/tags", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse
)
def get_tags(
    category_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_user_session),
    request: Request = None,
) -> schemas.SuccessResponse:

    result: InternalResponse = fetch_data_utils.get_tags(db, category_id)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            UsersTypes.TAGS, 
            status.HTTP_404_NOT_FOUND,
            message=result.message,
            details=None)
        
    return SuccessHTTPResponse.success_response(
        UsersTypes.TAGS, 
        result.message, 
        request)


@router.get(
    "/address-suggestions",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
@limiter.limit("10/minute")
async def get_address_suggestions(
    input: str, _: int = Depends(get_user_session), request: Request = None
) -> schemas.SuccessResponse:

    input = input.strip().lower()
    words = input.split(" ")
    contains_number = any(char.isdigit() for char in input)
    if words and len(words) >= 3 and not contains_number:
        fetched_suggestions = await maps_utils.fetch_geocode_data(input, True)
    else:
        fetched_suggestions = []

    if fetched_suggestions.get("status" == "error"):
        fetched_suggestions = []

    return schemas.SuccessResponse(
        message="Adress suggestions",
        data=fetched_suggestions,
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )
