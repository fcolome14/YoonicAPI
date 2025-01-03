from enum import IntEnum

from app.responses import SystemResponse, InternalResponse
from app.schemas.schemas import ResponseStatus
import inspect

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from typing import List

from datetime import datetime, timezone
from app.models import Categories, EventsHeaders
from app.schemas import NewPostHeaderInput, NewPostLinesInput, EventLines, NewPostLinesConfirmInput
from app.utils import maps_utils, utils, time_utils, fetch_data_utils
from app.services.common.structures import GenerateStructureService
from app.services.repeater_service import (select_repeater_single_mode,
                                           select_repeater_custom_mode)

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

        errors = HeaderPostsService._validate_header_basic_fields(posting_header)
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
    async def _validate_location(posting_header: NewPostHeaderInput, origin):
        if not posting_header.location:
            message = "A location must be provided"
            return SystemResponse.internal_response(ResponseStatus.ERROR, origin, message)
        
        result = utils.is_location_address(posting_header.location)
        if result.message:
            geodata: InternalResponse = await maps_utils.fetch_geocode_data(
                address=posting_header.location
            )
        else:
            geodata: InternalResponse = await maps_utils.fetch_reverse_geocode_data(
                lat=posting_header.location[0], lon=posting_header.location[1]
            )
        if geodata.status == ResponseStatus.ERROR:
            return geodata
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, geodata.message)

    @staticmethod
    def _validate_header_basic_fields(posting_header: NewPostHeaderInput, origin: str) -> InternalResponse:
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
            message = ", ".join(error_details)
            return SystemResponse.internal_response(ResponseStatus.ERROR, origin, message)
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, None)
    
    @staticmethod
    async def process_header(
        db: Session, user_id: int, posting_header: NewPostHeaderInput
    ):
        origin = inspect.stack()[0].function
        
        if (
            posting_header.status == HeaderStatus.NEW
            and posting_header.id == HeaderStatus.UNASSIGNED
        ):
            results: InternalResponse = HeaderPostsService._validate_header_basic_fields(
                posting_header, origin
            )
            if results.status == ResponseStatus.ERROR:
                return results
            results = await HeaderPostsService._validate_location(posting_header, origin)
            if results.status == ResponseStatus.ERROR:
                return results
        
            point, address = results.message["point"], results.message["address"]
            header = HeaderPostsService._add_header(db, point, address, user_id, posting_header)
            return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, header)
        
        elif posting_header.status == HeaderStatus.STAGING:
            return SystemResponse.internal_response(
                ResponseStatus.ERROR, 
                origin, 
                "Header already approved")
            
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Status not allowed in this process")
    
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
        
        header = HeaderPostsService._create_header(posting_header, point, address, user_id)
        
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

class LinesPostService:
    
    def __init__(self, user_id: int, posting_lines: NewPostLinesInput):
        
        payload: EventLines = self._get_lines_payload(posting_lines)
        
        self.header_id = posting_lines.header_id
        self.timezone = posting_lines.user_timezone
        self.user_id = user_id
        self.custom_each_day = posting_lines.custom_each_day
        self.custom_option_selected = posting_lines.custom_option_selected
        self.repeat = posting_lines.repeat
        self.occurrences = posting_lines.occurrences
        self.when_to = posting_lines.when_to
        self.for_days = posting_lines.for_days
        self.dates = []
        self.rates = []
        self.is_public = []
        self.capacity = []
        self.invited = []
        
        if not isinstance(payload, list):
            payload = [payload]
        
        for item in payload:
            self.dates.append((item.start, item.end))
            self.rates.append(item.rate)
            self.is_public.append(item.isPublic)
            self.capacity.append(item.capacity)
            self.invited.append(item.invited)
        
    def _get_lines_payload(
        self, 
        posting_lines: NewPostLinesInput):
        return posting_lines.line
        
    async def process_lines(
        self,
    ) -> InternalResponse:
        
        origin = inspect.stack()[0].function
        
        results: InternalResponse = self._validate_lines_basic_fields(origin)
        if results.status == ResponseStatus.ERROR:
            return results
        results = self._validate_dates_timezones(origin)
        if results.status == ResponseStatus.ERROR:
            return results
        lines = self._generate_post_lines()
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, lines)
    
    def _validate_lines_basic_fields(
        self,
        origin: str) -> InternalResponse:
        """
        Validate the basic fields of a post(s) line(s)

        Args:
            posting_lines (NewPostHeaderInput): Data for the new post header.

        Returns:
            list: List of error messages, if any.
        """
        error_details = []
        if not self.dates and len(self.dates) == 0:
            error_details.append("Date(s) field(s) are empty")
        if not self.is_public and len(self.is_public) == 0:
            error_details.append("Visibility field is empty")
        if not self.capacity and len(self.capacity) == 0:
            error_details.append("Capacity field is empty")
        if not self.rates and len(self.rates) == 0:
            error_details.append("Rate(s) field(s) are empty")
        if error_details:
            message = ", ".join(error_details)
            return SystemResponse.internal_response(ResponseStatus.ERROR, origin, message)
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, None)
    
    def _validate_dates_timezones(
        self,
        origin: str) -> InternalResponse:
        try:
            if isinstance(self.dates, list) and all(isinstance(pair, tuple) for pair in self.dates) and (len(pair) > 2 for pair in self.dates):
                self.dates = [
                    (
                        start.astimezone(timezone.utc) if isinstance(start, datetime)
                        else datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(timezone.utc),
                        end.astimezone(timezone.utc) if isinstance(end, datetime)
                        else datetime.fromisoformat(end.replace("Z", "+00:00")).astimezone(timezone.utc)
                    )
                    for start, end in self.dates
                    ]
                return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, self.dates)
            else:
                return SystemResponse.internal_response(ResponseStatus.ERROR, origin, "Invalid date data type")
        except Exception as exc:
            message = f"An error occurred: {str(exc)}"
            return SystemResponse.internal_response(ResponseStatus.ERROR, origin, message)
    
    def _generate_post_lines(self) -> InternalResponse:
        origin = inspect.stack()[0].function
        
        _result = self.dates
        if self.custom_option_selected:
            result: InternalResponse = self._custom_mode_enabled()
            if result.status == ResponseStatus.ERROR:
                return result
            _result = result.message
        if not self.custom_option_selected and self.repeat:
            result: InternalResponse = self._generate_repeated_schedule_single_mode()
            if result.status == ResponseStatus.ERROR:
                return result
            _result = result.message
            
        _result = self._pack_lines(_result)
            
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, _result)
    
    def _custom_mode_enabled(self) -> InternalResponse:
        origin = inspect.stack()[0].function
        
        if self.custom_each_day:
            result: InternalResponse = self._generate_customized_schedule_per_day()
            if result.status == ResponseStatus.ERROR:
                return result
        else:
            result: InternalResponse = self._generate_schedule_per_weekday()
            if result.status == ResponseStatus.ERROR:
                return result
        return SystemResponse.internal_response(
                ResponseStatus.SUCCESS, 
                origin, 
                result.message)
    
    def _generate_repeated_schedule_single_mode(self) -> InternalResponse:
        origin = inspect.stack()[0].function
        
        if len(self.dates) > 1:
            return SystemResponse.internal_response(
                ResponseStatus.ERROR, 
                origin, 
                "Expected dates list with a single item")
        result: InternalResponse = select_repeater_single_mode(self.when_to, self.dates, self.occurrences)
        if result.status == ResponseStatus.ERROR:
            return result
        return SystemResponse.internal_response(
                ResponseStatus.SUCCESS, 
                origin, 
                result.message) 
    
    def _generate_customized_schedule_per_day(self) -> InternalResponse:
        origin = inspect.stack()[0].function
        result = self.dates
        if self.repeat:
            results: InternalResponse = select_repeater_custom_mode(self.when_to, self.dates, self.occurrences)
            if results.status == ResponseStatus.ERROR:
                return results
            result = results.message
        return SystemResponse.internal_response(
                ResponseStatus.SUCCESS, 
                origin, 
                result)
    
    def _generate_schedule_per_weekday(self):
        origin = inspect.stack()[0].function
        start, end = self.dates[0]
        results: InternalResponse = time_utils.set_weekdays(start, end, self.for_days)
        if results.status == ResponseStatus.ERROR:
            return results
        
        if self.repeat:
            dates = results.message
            results: InternalResponse = select_repeater_custom_mode(self.when_to, dates, self.occurrences)
            if results.status == ResponseStatus.ERROR:
                return results
            
        return SystemResponse.internal_response(
                ResponseStatus.SUCCESS, 
                origin, 
                results.message)
    
    def _pack_lines(self, generated_lines: dict):
        def pack_single(key, value):
            result = get_visibility_capacity(key)
            return {
                "start": value[0] if not isinstance(value, list) else value[0][0],
                "end": value[1] if not isinstance(value, list) else value[0][1],
                "isPublic": result[0],
                "capacity": result[1],
                "rates": self.rates[int(key)] if (self.custom_option_selected and self.custom_each_day) else self.rates
            }

        def pack_repeated(key, value, is_pub, cap):
            return [
                {
                    "start": pair[0],
                    "end": pair[1],
                    "isPublic": is_pub,
                    "capacity": cap,
                    "rates": self.rates[int(key)] if (self.custom_option_selected and self.custom_each_day) else self.rates
                }
                for pair in value
            ]
        
        def get_visibility_capacity(key: int):
            isPublic, capacity = "", ""
            if isinstance(self.is_public, list) and len(self.is_public) > 1:
                isPublic = self.is_public[key]
            elif isinstance(self.is_public, list) and len(self.is_public) == 1:
                isPublic = self.is_public[0]
            
            if isinstance(self.capacity, list) and len(self.capacity) > 1:
                capacity = self.capacity[key]
            elif isinstance(self.capacity, list) and len(self.capacity) == 1:
                capacity = self.capacity[0]
            return (isPublic, capacity)
        
        if not self.repeat and not self.custom_option_selected:
            return {
                key: pack_single(key, value)
                for key, value in enumerate(generated_lines)
            }
        
        if self.repeat and not self.custom_option_selected:
            return {
                key: pack_repeated(key, value, is_pub, cap)
                for (key, value), is_pub, cap in zip(generated_lines.items(), self.is_public, self.capacity)
            }

        if self.repeat and not self.custom_option_selected and self.custom_each_day:
            return {
                key: pack_repeated(key, value, is_pub, cap)
                for (key, value), is_pub, cap in zip(generated_lines.items(), self.is_public, self.capacity)
            }
        
        if self.repeat and self.custom_option_selected and self.custom_each_day:
            return {
                key: pack_repeated(key, value, is_pub, cap)
                for (key, value), is_pub, cap in zip(generated_lines.items(), self.is_public, self.capacity)
            }

        if self.custom_option_selected and not self.repeat and not self.custom_each_day:
            return {
                key: pack_single(key, value)
                for key, value in enumerate(generated_lines.items())
            }
        
        if self.custom_option_selected and not self.repeat and self.custom_each_day:
            return {
                key: pack_single(key, value)
                for key, value in enumerate(generated_lines)
            }

        if self.repeat and not self.custom_each_day and self.custom_option_selected:
            return {
                key: pack_repeated(key, value, is_pub, cap)
                for (key, value), is_pub, cap in zip(generated_lines.items(), self.is_public, self.capacity)
            }
class PostConfirmation:
    def __init__(self, user_id: int, posting_data: NewPostLinesConfirmInput):
        self.user_id = user_id
        self.posting_data = posting_data
    

    def add_post(self, db: Session):
        origin = inspect.stack()[0].function
        result: InternalResponse = fetch_data_utils.add_post(
                                         db, 
                                         self.user_id, 
                                         self.posting_data.header_id, 
                                         self.posting_data.lines)
        if result.status == ResponseStatus.ERROR:
            return result
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, result.message)
        
        
            
