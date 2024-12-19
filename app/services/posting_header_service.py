from sqlalchemy.orm import Session

from app.models import Categories
from app.schemas import NewPostHeaderInput, UpdatePostInput
from app.utils import maps_utils, utils


class PostingHeaderService:

    @staticmethod
    async def _check_inputs(
        db: Session, user_id: int, posting_header: NewPostHeaderInput
    ):
        posting_header.title = posting_header.title.strip()
        posting_header.description = posting_header.description.strip()

        error_details = []
        if not posting_header.title:
            error_details.append("Title field is empty")
        if not posting_header.description:
            error_details.append("Description field is empty")
        if not posting_header.category:
            error_details.append("Category field is empty")

        if error_details:
            return {"status": "error", "details": ", ".join(error_details)}

        category = (
            db.query(Categories)
            .filter(Categories.id == posting_header.category)
            .first()
        )
        if not category:
            return {"status": "error", "details": "Category not found"}

        response = await PostingHeaderService._check_location(posting_header)
        if response.get("status") == "error":
            return {"status": "error", "details": response.get("details")}
        return {
            "status": "success",
            "details": (response.get("point"), response.get("address")),
        }

    @staticmethod
    async def _check_location(posting_header: NewPostHeaderInput):
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
