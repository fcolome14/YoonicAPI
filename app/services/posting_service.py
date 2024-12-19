from enum import IntEnum

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from app.models import Categories, EventsHeaders
from app.schemas import NewPostHeaderInput, UpdatePostInput
from app.services.event_service import EventService, EventUpdateService
from app.services.posting_header_service import PostingHeaderService
from app.services.retrieve_service import RetrieveService
from app.utils import maps_utils, utils


class HeaderStatus(IntEnum):
    NEW = 0
    STAGING = 1
    UNASSIGNED = -1


class PostService:
    @staticmethod
    async def process_header(
        db: Session, user_id: int, posting_header: NewPostHeaderInput
    ):

        if (
            posting_header.status == HeaderStatus.NEW
            and posting_header.id == HeaderStatus.UNASSIGNED
        ):
            results = await PostingHeaderService._check_inputs(
                db, user_id, posting_header
            )
            if results.get("status") == "error":
                return results

            point, address = results.get("details")[0], results.get("details")[1]
            header = EventsHeaders(
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

            db.add(header)
            db.commit()
            db.refresh(header)
            header = RetrieveService.generate_header_structure(header)
            return {"status": "success", "message": "Approved header", "header": header}

        elif posting_header.status == HeaderStatus.STAGING:
            return {"status": "error", "details": "Header already approved"}
        return {"status": "error", "details": "Status not allowed in this process"}

        # result = EventService.generate_post_lines(db=db, posting_data=posting_data, header_id=header.id)
        # if result.get("status") == "error":
        #     return {"status": "error", "details": result.get("details")}
        # return {"status": "success", "details": result.get("details")}

    @staticmethod
    async def update_post_data(
        user_id: int, update_data: UpdatePostInput, db: Session
    ) -> dict:
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
                update_header = await EventUpdateService._update_header(
                    db, user_id, item.table, item.changes
                )
            elif item.table == 1:
                update_lines = await EventUpdateService._update_lines(
                    db, user_id, item.table, item.changes
                )
            elif item.table == 2:
                update_rates = await EventUpdateService._update_rates(
                    db, user_id, item.table, item.changes
                )

        return {
            "status": "success",
            "details": (update_header, update_lines, update_rates),
        }
