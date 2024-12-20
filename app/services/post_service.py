from enum import IntEnum

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from typing import List

from app.models import Categories, EventsHeaders
from app.schemas import NewPostHeaderInput
from app.utils import maps_utils, utils
from app.services.common.structures import GenerateStructureService

class HeaderStatus(IntEnum):
    UNASSIGNED = -1
    NEW = 0
    STAGING = 1
    REVISION = 2
    APPROVED = 3
    
class HeaderPostsService:

    @staticmethod
    async def validate_header_inputs(
        db: Session, posting_header: NewPostHeaderInput
    ):
        posting_header.title = posting_header.title.strip()
        posting_header.description = posting_header.description.strip()

        errors = HeaderPostsService._validate_basic_fields(posting_header)
        if errors:
            return errors

        category = (
            db.query(Categories)
            .filter(Categories.id == posting_header.category)
            .first()
        )
        if not category:
            return {"status": "error", "details": "Category not found"}

        response = await HeaderPostsService._validate_location(posting_header)
        if response.get("status") == "error":
            return {"status": "error", "details": response.get("details")}
        
        return {
            "status": "success",
            "details": (response.get("point"), response.get("address")),
        }

    @staticmethod
    async def _validate_location(posting_header: NewPostHeaderInput):
        if not posting_header.location:
            return {"status": "error", "details": "A location must be provided"}
        
        if utils.is_location_address(posting_header.location):
            geodata = await maps_utils.fetch_geocode_data(
                address=posting_header.location
            )
        else:
            geodata = await maps_utils.fetch_reverse_geocode_data(
                lat=posting_header.location[0], lon=posting_header.location[1]
            )
        if geodata.get("status") == "error":
            return {"status": "error", "details": geodata.get("details")}
        
        return geodata

    @staticmethod
    def fetch_pending_headers(db: Session, user_id: int):
        fetched_header = (
        db.query(EventsHeaders)
        .filter(
            and_(
                EventsHeaders.status == 1,
                EventsHeaders.owner_id == user_id,
            )
        )
        .first()
        )

        if not fetched_header:
            message, header = "No pending headers", None
        else:
            message, header = (
                "Found pending headers",
                GenerateStructureService.generate_header_structure(fetched_header),
            )
        
        return {"status": "success", "details": (message, header)}

    @staticmethod
    def _validate_basic_fields(posting_header: NewPostHeaderInput) -> list:
        """
        Validate the basic fields of a post header

        Args:
            posting_header (NewPostHeaderInput): Data for the new post header.

        Returns:
            list: List of error messages, if any.
        """
        error_details = []
        if not posting_header.title:
            error_details.append("Title field is empty")
        if not posting_header.description:
            error_details.append("Description field is empty")
        if not posting_header.category:
            error_details.append("Category field is empty")

        if error_details:
            return {"status": "error", "details": ", ".join(error_details)}
        return None
    
    @staticmethod
    async def process_header(
        db: Session, user_id: int, posting_header: NewPostHeaderInput
    ):

        if (
            posting_header.status == HeaderStatus.NEW
            and posting_header.id == HeaderStatus.UNASSIGNED
        ):
            results = HeaderPostsService._validate_basic_fields(
                db, user_id, posting_header
            )
            if results["status"] == "error":
                return results
            results = await HeaderPostsService._validate_location(posting_header)
            if results["status"] == "error":
                return results
            
            point, address = results["point"], results["address"]
            header = HeaderPostsService._add_header(db, point, address, user_id, posting_header)
            return {"status": "success", "details": {"message": "Approved header", "header": header}}

        elif posting_header.status == HeaderStatus.STAGING:
            return {"status": "error", "details": "Header already approved"}
        return {"status": "error", "details": "Status not allowed in this process"}
    
    @staticmethod
    def _create_header(
        posting_header: NewPostHeaderInput, 
        point: List[float], 
        address: str, 
        user_id: int,):
        
        return EventsHeaders(
                title=posting_header.title,
                description=posting_header.description,
                address=address,
                coordinates=f"{point[0]}, {point[1]}",
                geom=func.ST_SetSRID(func.ST_Point(point[1], point[0]), 4326),
                owner_id=user_id,
                category=posting_header.category,
                status=1,
                score=0,  # DELETE FROM TABLE
            )
    
    @staticmethod
    def _add_header(
        db: Session,
        point: List[float], 
        address: str, 
        user_id: int,
        posting_header: NewPostHeaderInput):
        
        header = HeaderPostsService._create_header(point, address, user_id, posting_header)
        
        db.add(header)
        db.commit()
        db.refresh(header)
        
        return GenerateStructureService.generate_header_structure(header)
    
    # @staticmethod
    # async def update_post_data(
    #     user_id: int, update_data: UpdatePostInput, db: Session
    # ) -> dict:
    #     """Update post data if there are changes

    #     Args:
    #         user_id (int): Owner of the post
    #         update_data (schemas.UpdatePostInput): Schema with all new data to be updated
    #         db (Session): Database connection

    #     Returns:
    #         dict: Information about failures or successful changes applied
    #     """
    #     for item in update_data.tables:
    #         if item.table == 0:
    #             update_header = await EventUpdateService._update_header(
    #                 db, user_id, item.table, item.changes
    #             )
    #         elif item.table == 1:
    #             update_lines = await EventUpdateService._update_lines(
    #                 db, user_id, item.table, item.changes
    #             )
    #         elif item.table == 2:
    #             update_rates = await EventUpdateService._update_rates(
    #                 db, user_id, item.table, item.changes
    #             )

    #     return {
    #         "status": "success",
    #         "details": (update_header, update_lines, update_rates),
    #     }
