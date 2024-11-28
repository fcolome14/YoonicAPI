from fastapi import HTTPException, APIRouter, status, Depends, Request
from sqlalchemy.orm import Session
from app.database.connection import get_db
import pytz
from app.schemas import schemas
from app.oauth2 import get_user_session
from app.utils import time_utils, utils, maps_utils
import app.models as models

router = APIRouter(prefix="/posts", tags=["Posts"])
utc = pytz.UTC

@router.post("/new-post", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse)
async def create_post(posting_data: schemas.NewPostInput, db: Session = Depends(get_db), _: int = Depends(get_user_session), request: Request = None):
    
    if not time_utils.is_start_before_end(posting_data.start, posting_data.end):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=schemas.ErrorDetails(
                                type="NewPost",
                                message="Invalid datetimes",
                                details="Starting date must be before ending date").model_dump())
    
    if utils.is_location_address(posting_data.location):
        geodata = await maps_utils.fetch_geocode_data(address=posting_data.location)
    else:
        geodata = await maps_utils.fetch_reverse_geocode_data(lat=posting_data.location[0], lon=posting_data.location[1])
    
    if geodata.get("status") == "error":
            raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=schemas.ErrorDetails(
                type="OSM",
                message=geodata.get("details"),
                details=None
            ).model_dump()
        )
    
    posting_data_dict = posting_data.model_dump()
    posting_data_dict.pop("location", None)
    
    new_post = models.Events(
        **posting_data_dict,
        address=geodata.get("address"),
        coordinates=geodata.get("point")
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    return schemas.SuccessResponse(
        status="success",
        message="New event created",
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )