from sqlalchemy.orm import Session
from app.schemas import NewPostInput, UpdatePostInput
from app.models import EventsHeaders
from app.services.event_service import EventService, EventUpdateService
from app.utils import utils, maps_utils
from sqlalchemy import func

class PostService:
    @staticmethod
    async def create_post(db: Session, user_id: int, posting_data: NewPostInput):
        # Geocoding
        if utils.is_location_address(posting_data.location):
            geodata = await maps_utils.fetch_geocode_data(address=posting_data.location)
        else:
            geodata = await maps_utils.fetch_reverse_geocode_data(
                lat=posting_data.location[0], lon=posting_data.location[1]
            )

        if geodata.get("status") == "error":
            return {"status": "error", "details": geodata.get("details")}

        header = EventsHeaders(
            title=posting_data.title,
            description=posting_data.description,
            address=geodata.get("address"),
            coordinates=f'{geodata.get("point")[0]},{geodata.get("point")[1]}',
            geom=func.ST_SetSRID(
                func.ST_Point(geodata.get("point")[1], geodata.get("point")[0]), 4326
            ),
            owner_id=user_id,
            category=posting_data.category,
        )

        db.add(header)
        db.commit()
        db.refresh(header)

        result = EventService.generate_post_lines(db=db, posting_data=posting_data, header_id=header.id)

        if result.get("status") == "error":
            return {"status": "error", "details": result.get("details")}

        return {"status": "success", "details": result.get("details")}
    
    @staticmethod
    async def update_post_data(user_id: int, update_data: UpdatePostInput, db: Session) -> dict:
        """Update post data if there are changes

        Args:
            user_id (int): Owner of the post
            update_data (schemas.UpdatePostInput): Schema with all new data to be updated
            db (Session): Database connection

        Returns:
            dict: Information about failures or successful changes applied
        """
        for item in update_data.tables:
            if item.table == 0:
                update_header = await EventUpdateService._update_header(db, user_id, item.table, item.changes)
            elif item.table == 1:
                update_lines = await EventUpdateService._update_lines(db, user_id, item.table, item.changes)
            elif item.table == 2:
                update_rates = await EventUpdateService._update_rates(db, user_id, item.table, item.changes)
                
            
        
        return {"status": "success", "details": (update_header, update_lines, update_rates)}

