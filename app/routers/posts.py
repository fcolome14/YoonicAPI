import pytz
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session
from app.schemas.schemas import ResponseStatus
from app.schemas.schemas import InternalResponse

import app.models as models
from app.database.connection import get_db
from app.oauth2 import get_user_session
from app.schemas import schemas
from app.services.event_service import EventDeleteService
from app.services.retrieve_service import RetrieveService
from app.responses import SuccessHTTPResponse, ErrorHTTPResponse
from app.templates.template_service import HTMLTemplates
from app.utils import email_utils, fetch_data_utils
from app.services.post_service import (
    HeaderPostsService, 
    LinesPostService, 
    PostConfirmation, 
    UpdatePost)

router = APIRouter(prefix="/posts", tags=["Posts"])
utc = pytz.UTC


@router.get(
    "/new-post", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse
)
def new_post(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_session),
    request: Request = None,
):
    result: InternalResponse = fetch_data_utils.pending_headers(db, user_id) 
    return SuccessHTTPResponse.success_response("Fetch any pending header", result.message, request)

@router.post(
    "/create-header",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
async def create_header(
    posting_data: schemas.NewPostHeaderInput,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_session),
    request: Request = None,
):
    result: InternalResponse = await HeaderPostsService.process_header(
        db=db, user_id=user_id, posting_header=posting_data
    )
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            "CreateHeader", status.HTTP_500_INTERNAL_SERVER_ERROR, result.message, None
        )
    return SuccessHTTPResponse.success_response("CreateHeader", result.message, request)

@router.post(
    "/create-lines",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
async def create_lines(
    posting_data: schemas.NewPostLinesInput,
    user_id: int = Depends(get_user_session),
    request: Request = None,
):
    lines = LinesPostService(user_id, posting_data)
    result: InternalResponse = await lines.process_lines()
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            "CreateLines", status.HTTP_500_INTERNAL_SERVER_ERROR, result.message, None
        )
    generated_lines: InternalResponse = result.message.message
    return SuccessHTTPResponse.success_response("CreateLines", generated_lines, request)

@router.post(
    "/confirm-post",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
def confirm_post(
    posting_data: schemas.NewPostLinesConfirmInput,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_session),
    request: Request = None,
):
    post = PostConfirmation(user_id, posting_data)
    result: InternalResponse = post.add_post(db)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            "ConfirmPost", status.HTTP_500_INTERNAL_SERVER_ERROR, result.message, None
        )
    return SuccessHTTPResponse.success_response("ConfirmPost", "Post created successfully", request)

@router.get(
    "/nearby-events",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
def nearby_events(
    lat: float,
    lon: float,
    radius: int = 10,
    unit: int = 0,
    db: Session = Depends(get_db),
    request: Request = None,
    _: int = Depends(get_user_session),
):

    events_within_area, reference_point = RetrieveService.get_events_within_area(
        db, lat, lon, radius, unit
    )

    if events_within_area.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=schemas.ErrorDetails(
                type="GetNearbyEvents",
                message=events_within_area.get("details"),
                details=None,
            ).model_dump(),
        )

    header, lines = events_within_area.get("details")
    response = RetrieveService.generate_nearby_events_structure(
        db, header, lines, reference_point, unit
    )
    if not response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=schemas.ErrorDetails(
                type="GetNearbyEvents", message="Events not found", details=None
            ).model_dump(),
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
        },
    )


@router.get(
    "/owned-events",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
def owned_events(
    lat: float,
    lon: float,
    db: Session = Depends(get_db),
    request: Request = None,
    user_id: int = Depends(get_user_session),
):

    fetched_headers = (
        db.query(models.EventsHeaders)
        .filter(and_(models.EventsHeaders.owner_id == user_id))
        .all()
    )
    header_ids = [item.id for item in fetched_headers]
    current_pos = (lat, lon)
    fetched_lines = (
        db.query(models.EventsLines)
        .filter(and_(models.EventsLines.header_id.in_(header_ids)))
        .all()
    )
    # TODO: FILTER BY ACTIVE EVENTS
    response = RetrieveService.generate_nearby_events_structure(
        db, fetched_headers, fetched_lines, current_pos, 0
    )
    if not response:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=schemas.ErrorDetails(
                type="GetOwnEvents", message="Events not found", details=None
            ).model_dump(),
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
        },
    )


@router.get(
    "/event-details",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
def get_event_details(
    event_id: int,
    lat: float,
    lon: float,
    radius: int = 10,
    unit: int = 0,
    db: Session = Depends(get_db),
    request: Request = None,
    user_id: int = Depends(get_user_session),
):

    selected_event, related_events = RetrieveService.generate_details_events_structure(
        db, event_id, lat, lon, radius, user_id, unit
    )

    return schemas.SuccessResponse(
        status="success",
        message="Event and suggested events",
        data={
            "selected_event": selected_event,
            "total_related_events": len(related_events),
            "related_events": related_events,
        },
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )


@router.delete("/delete-event", response_model=schemas.SuccessResponse)
def delete_event(
    delete_data: schemas.DeletePostInput,
    db: Session = Depends(get_db),
    request: Request = None,
    user_id: int = Depends(get_user_session),
):

    result = EventDeleteService.delete_events(db, delete_data, user_id)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=schemas.ErrorDetails(
                type="DeletionPost", message=result.get("details"), details=None
            ).model_dump(),
        )

    # NOTIFY SUBS USERS VIA EMAIL THAT THE EVENT HAS BEEN REMOVED
    return schemas.SuccessResponse(
        status="success",
        message=result.get("details"),
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )


@router.put(
    "/update-event",
    response_model=schemas.SuccessResponse,
    status_code=status.HTTP_200_OK,
)
async def update_event(
    updated_data: schemas.UpdatePostInput,
    db: Session = Depends(get_db),
    request: Request = None,
    user_id: int = Depends(get_user_session),
):

    tracked_changes = await UpdatePost.update_post_data(
    db, user_id, updated_data)

    if tracked_changes.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            "UpdateEvent", 
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            tracked_changes.message, None
        )
    tracked_changes = tracked_changes.message
    return SuccessHTTPResponse.success_response("PostUpdate", tracked_changes, request)

@router.put(
    "/confirm-update",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
def confirm_update(
    confirmed_data: schemas.UpdatePostConfirmInput,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_session),
    request: Request = None,
    ):
    
    if not confirmed_data.data:
        message = "No changes applied"
        return SuccessHTTPResponse.success_response("ConfirmUpdate", message, request)
    
    result: InternalResponse = PostConfirmation.update_db(db, user_id, confirmed_data.data)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            "ConfirmUpdate", 
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            result.message, None
        )
    updated_changes = result.message
    result = PostConfirmation.build_post_updates_structure(updated_changes)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            "ConfirmUpdate", 
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            result.message, None
        )
    updated_changes = result.message
    result = email_utils.send_updated_events(db, user_id, updated_changes)
    if result.status == ResponseStatus.ERROR:
        raise ErrorHTTPResponse.error_response(
            "ConfirmUpdate", 
            status.HTTP_500_INTERNAL_SERVER_ERROR, 
            result.message, None
        )
    
    return SuccessHTTPResponse.success_response("ConfirmUpdate", result.message, request)