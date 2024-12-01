from fastapi import HTTPException, APIRouter, status, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy import func
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
    
    coordinates = geodata.get("point")
    geom = func.ST_SetSRID(func.ST_Point(coordinates[0], coordinates[1]), 4326)
    
    new_post = models.Events(
        **posting_data_dict,
        address=geodata.get("address"),
        coordinates=f'{coordinates[0]},{coordinates[1]}',
        geom=geom,
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

    
@router.get("/nearby-events", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse)
def nearby_events(lat: float, lon: float, radius: int = 10, unit: int = 0, db: Session = Depends(get_db), request: Request = None, _: int = Depends(get_user_session)):
    
    reference_point = [lat, lon]
    area = maps_utils.get_bounding_area(point=reference_point, radius=radius)
    events_within_area = maps_utils.get_within_events(area, db=db)
    
    if events_within_area.get("status") == "error":
        #ERROR
        pass
    
    event_data = []
    for event in events_within_area.get("details"):
        try:
            lat, lon = event.get("coordinates").split(",")
            event_coordinates = float(lat), float(lon)
        except ValueError:
            event_coordinates = (0.0, 0.0)
            
        event_dict = {
            "id": event.get("id"),
            "title": event.get("title"),
            "description": event.get("description"),
            "address": event.get("address"),
            "start": event.get("start").strftime("%Y-%m-%d %H:%M:%S"),
            "end": event.get("end").strftime("%Y-%m-%d %H:%M:%S"),
            "coordinates": event.get("coordinates"),
            "img": event.get("img"),
            "img2": event.get("img2"),
            "cost": event.get("cost"),
            "capacity": event.get("capacity"),
            "currency": event.get("currency"),
            "isPublic": event.get("isPublic"),
            "owner_id": event.get("owner_id"),
            "category": event.get("category"),
            "distance": maps_utils.compute_distance(pointA=reference_point, pointB=event_coordinates, units=unit),
            "distance_unit": "km" if unit == 0 else "miles"
            }
        event_data.append(event_dict)

    return schemas.SuccessResponse(
        status="success",
        message="Fetched nearby events",
        data={
            "total": len(event_data),
            "detail": event_data,
            },
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )

@router.get("/owned-events", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse)
def owned_events(db: Session = Depends(get_db), request: Request = None, user_id: int = Depends(get_user_session)):
    
    fetched_posts = db.query(models.Events).filter(models.Events.owner_id == user_id).all()
    
    event_data = []
    for event in fetched_posts:
        event_dict = {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "address": event.address,
            "start": event.start,
            "end": event.end,
            "coordinates": event.coordinates,
            "img": event.img,
            "img2": event.img2,
            "cost": event.cost,
            "capacity": event.capacity,
            "currency": event.currency,
            "isPublic": event.isPublic,
            "category": event.category,
            }
        event_data.append(event_dict)
        
    
    if not fetched_posts:
        #ERROR
        pass

    return schemas.SuccessResponse(
        status="success",
        message="Fetched owned events",
        data={
            "total": len(event_data),
            "detail": event_data,
            },
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )

@router.get("/event_details", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse)
def get_event_details(event_id: int, lat: float, lon: float, radius: int = 10, unit: int = 0, 
                      db: Session = Depends(get_db), request: Request = None, _: int = Depends(get_user_session)):
    
    reference_point = [lat, lon]
    related_events = []
    area = maps_utils.get_bounding_area(point=reference_point, radius=radius, units=unit)
    
    events_within_area = maps_utils.get_within_events(area, db=db)
    if not events_within_area:
        nearby_event_ids = []
    else:
        nearby_event_ids = [event.get("id") for event in events_within_area.get("details", []) if event.get("id") != event_id]

    fetched_post = db.query(models.Events).filter(models.Events.id == event_id).first()
    if not fetched_post:
        event_dict = {}
    else:
        fetched_related_posts = db.query(models.Events).filter(
            and_(models.Events.id.in_(nearby_event_ids), 
                 models.Events.isPublic == True, # noqa: E712
                 models.Events.category == fetched_post.category)).all()
        
        try:
            event_lat, event_lon = fetched_post.coordinates.split(",")
            event_coordinates = float(event_lat), float(event_lon)
        except ValueError:
            event_coordinates = (0.0, 0.0)
            
        event_dict = {
            "id": fetched_post.id,
            "title": fetched_post.title,
            "description": fetched_post.description,
            "address": fetched_post.address,
            "start": fetched_post.start.strftime("%Y-%m-%d %H:%M:%S") if fetched_post.start else None,
            "end": fetched_post.end.strftime("%Y-%m-%d %H:%M:%S") if fetched_post.end else None,
            "coordinates": fetched_post.coordinates,
            "img": fetched_post.img,
            "img2": fetched_post.img2,
            "cost": fetched_post.cost,
            "capacity": fetched_post.capacity,
            "currency": fetched_post.currency,
            "isPublic": fetched_post.isPublic,
            "category": fetched_post.category,
            "distance": maps_utils.compute_distance(pointA=event_coordinates, pointB=(lat, lon), units=unit),
            "distance_unit": "km" if unit == 0 else "miles"
        }
        
        if not fetched_related_posts:
            related_events = []
        else:
            related_events = [
                {
                    "id": related_event.id,
                    "category": related_event.category,
                    "title": related_event.title,
                    "address": related_event.address,
                    "start": related_event.start.strftime("%Y-%m-%d %H:%M:%S") if related_event.start else None,
                    "end": related_event.end.strftime("%Y-%m-%d %H:%M:%S") if related_event.end else None,
                    "img": related_event.img,
                    "img2": related_event.img2,
                }
                for related_event in fetched_related_posts
            ]
    
    return schemas.SuccessResponse(
        status="success",
        message="Event and suggested events",
        data={
            "selected_event": event_dict,
            "related_events": related_events
        },
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )


@router.delete("/owned-event", response_model=schemas.SuccessResponse)
def delete_event(event_id: int, db: Session = Depends(get_db), request: Request = None, user_id: int = Depends(get_user_session)):
    
    fetched_posts = db.query(models.Events).filter(and_(models.Events.owner_id == user_id, models.Events.id == event_id)).first()
    
    if not fetched_posts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=schemas.ErrorDetails(
                type="DeletionPost",
                message="Event not found",
                details=None
            ).model_dump()
        )
    
    db.delete(fetched_posts)
    db.commit()
    
    #NOTIFY SUBS USERS VIA EMAIL THAT THE EVENT HAS BEEN REMOVED

    return schemas.SuccessResponse(
        status="success",
        message="Deleted event successfully",
        data={},
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )

@router.put("/owned-event", response_model=schemas.SuccessResponse, status_code=status.HTTP_200_OK)
def update_event(updated_data: schemas.UpdatePostInput, db: Session = Depends(get_db), request: Request = None, user_id: int = Depends(get_user_session)):
    
    result = utils.update_post_data(user_id=user_id, update_data=updated_data, db=db)
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=schemas.ErrorDetails(
                type="UpdatePost",
                message=result.get("details"),
                details=None
            ).model_dump()
        )
        
    applied_changes = result.get("details")
    if updated_data.notifyUsers:
        #SEND EMAIL TO ALL USERS SUBS TO WARN THEM OF THE CHANGES
        pass
    
    return schemas.SuccessResponse(
        status="success",
        message="Event updated successfully",
        data=applied_changes,
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )