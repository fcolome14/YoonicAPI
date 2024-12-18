from fastapi import HTTPException, APIRouter, status, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.database.connection import get_db
import pytz
from app.schemas import schemas
from app.oauth2 import get_user_session
from app.utils import time_utils, maps_utils, email_utils
import app.models as models
from datetime import datetime
from app.services.posting_service import PostService, EventUpdateService
from app.services.retrieve_service import RetrieveService
from app.services.event_service import EventDeleteService

router = APIRouter(prefix="/posts", tags=["Posts"])
utc = pytz.UTC

@router.post("/new-post", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse)
async def create_post(
    posting_data: schemas.NewPostInput,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_session),
    request: Request = None,
):
    result = await PostService.create_post(db=db, user_id=user_id, posting_data=posting_data)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=schemas.ErrorDetails(
                type="OSM",
                message=result.get("details"),
                details=None,
            ).model_dump(),
        )
        
    return schemas.SuccessResponse(
        status="success",
        message="New event created",
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )

@router.get("/nearby-events", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse)
def nearby_events(lat: float, lon: float, radius: int = 10, unit: int = 0,
                  db: Session = Depends(get_db), request: Request = None, _: int = Depends(get_user_session)):
    
    events_within_area, reference_point = RetrieveService.get_events_within_area(db, lat, lon, radius, unit)
    
    if events_within_area.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=schemas.ErrorDetails(
                type="GetNearbyEvents",
                message=events_within_area.get("details"),
                details=None
            ).model_dump()
        )
    
    header, lines = events_within_area.get("details")
    response = RetrieveService.generate_nearby_events_structure(db, header, lines, reference_point, unit)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=schemas.ErrorDetails(
                type="GetNearbyEvents",
                message="Events not found",
                details=None
            ).model_dump()
        )
    
    return schemas.SuccessResponse(
        status="success",
        message="Fetched nearby events",
        data={
            "total": len(response),
            "detail": response,
            },
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )

@router.get("/owned-events", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse)
def owned_events(lat: float, lon: float, db: Session = Depends(get_db), request: Request = None, user_id: int = Depends(get_user_session)):
    
    fetched_headers = db.query(models.EventsHeaders).filter(and_(models.EventsHeaders.owner_id == user_id)).all()
    header_ids = [item.id for item in fetched_headers]
    current_pos = (lat, lon)
    fetched_lines = db.query(models.EventsLines).filter(and_(models.EventsLines.header_id.in_(header_ids))).all()
    #TODO: FILTER BY ACTIVE EVENTS
    response = RetrieveService.generate_nearby_events_structure(db, fetched_headers, fetched_lines, current_pos, 0)
    if not response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=schemas.ErrorDetails(
                type="GetOwnEvents",
                message="Events not found",
                details=None
            ).model_dump()
        )

    return schemas.SuccessResponse(
        status="success",
        message="Fetched owned events",
        data={
            "total": len(response),
            "detail": response,
            },
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )

@router.get("/event-details", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse)
def get_event_details(event_id: int, lat: float, lon: float, radius: int = 10, unit: int = 0, 
                      db: Session = Depends(get_db), request: Request = None, user_id: int = Depends(get_user_session)):
    
    selected_event, related_events = RetrieveService.generate_details_events_structure(db, event_id, lat, lon, radius, user_id, unit)
    
    return schemas.SuccessResponse(
        status="success",
        message="Event and suggested events",
        data={
            "selected_event": selected_event,
            "total_related_events": len(related_events),
            "related_events": related_events
        },
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )

@router.delete("/delete-event", response_model=schemas.SuccessResponse)
def delete_event(delete_data: schemas.DeletePostInput, db: Session = Depends(get_db), request: Request = None, user_id: int = Depends(get_user_session)):
    
    result = EventDeleteService.delete_events(db, delete_data, user_id)
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=schemas.ErrorDetails(
                type="DeletionPost",
                message=result.get("details"),
                details=None
            ).model_dump()
        )
    
    #NOTIFY SUBS USERS VIA EMAIL THAT THE EVENT HAS BEEN REMOVED
    return schemas.SuccessResponse(
        status="success",
        message=result.get("details"),
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )

@router.put("/update-event", response_model=schemas.SuccessResponse, status_code=status.HTTP_200_OK)
async def update_event(updated_data: schemas.UpdatePostInput, db: Session = Depends(get_db), request: Request = None, user_id: int = Depends(get_user_session)):
    
    raw_changes = await PostService.update_post_data(user_id=user_id, update_data=updated_data, db=db)
    
    if raw_changes.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=schemas.ErrorDetails(
                type="UpdatePost",
                message=raw_changes.get("details"),
                details=None
            ).model_dump()
        )
    
    filtered_changes = EventUpdateService.group_changes_by_event(raw_changes)
    result_email = {}
    if len(filtered_changes) > 0:
        message = "Sent event update email"
        result_email = email_utils.send_updated_events(db, user_id, filtered_changes)
    else:
        message = "Event unchanged. Email not sent"    
    
    return schemas.SuccessResponse(
        status="success",
        message=message,
        data=result_email,
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )