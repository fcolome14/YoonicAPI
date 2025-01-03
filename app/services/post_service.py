from enum import IntEnum, Enum
from functools import wraps

from app.responses import SystemResponse, InternalResponse
from app.schemas import ResponseStatus, UpdateChanges
import inspect

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from typing import List

from datetime import datetime, timezone
from app.models import Categories, EventsHeaders
from app.schemas import (
    NewPostHeaderInput, 
    NewPostLinesInput, 
    EventLines, 
    NewPostLinesConfirmInput, 
    UpdatePostInput)
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

class UpdateStatus(Enum):
    ERROR = "error"
    SUCCESS = "success"

class SourceTable(Enum):
    HEADER = "events_headers"
    LINES = "events_lines"
    RATES = "rates"
    
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
    
    @staticmethod
    async def _update_header(
        db: Session, 
        source: str,
        user_id: int, 
        table: int, 
        changes: UpdateChanges = None
    ) -> InternalResponse:
        """
        Update header entry-point

        Args:
            db (Session): Connection Session
            user_id (int): User unique id
            table (int): Db table number (events_header = 0)
            changes (UpdateChanges, optional): Changes applied to the table. Defaults to None.

        Returns:
            InternalResponse: Internal response
        """
        origin = inspect.stack()[0].function
         
        if not changes:
            return SystemResponse.internal_response(
                ResponseStatus.ERROR,
                origin, 
                F"No changes applied to {SourceTable.HEADER.value}")
            
        if table != 0:
            return SystemResponse.internal_response(
                ResponseStatus.ERROR,
                origin, 
                f"Invalid specification table. Expected {SourceTable.HEADER.value}")

        header_id, updates = [item.id for item in changes], [item.update for item in changes]
        result: InternalResponse = fetch_data_utils.get_header(db, user_id, header_id[0])
        if result.status == ResponseStatus.ERROR:
            return result
        
        header: EventsHeaders = result.message
        result = await HeaderPostsService._track_header_changes(db, source, updates, header)
        if result.status == ResponseStatus.ERROR:
            return result
        
        db.commit()
        
        tracked_changes = result.message
        message = f"No changes applied to {SourceTable.HEADER.value}"
        if len(tracked_changes) > 0:
            message = tracked_changes
        return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            message)
        
    async def _track_header_changes(
        db: Session, 
        source: str,
        updates: list, 
        header: EventsHeaders, 
    ) -> InternalResponse:
        
        tracked_changes = []
        origin = inspect.stack()[0].function
        
        for update in updates[0]:
            field = update.field
            new_value = update.value
            old_value = getattr(header, field, None)
            allowed_fields = ["title", "description", "coordinates", "address", "category", "img", "img2"]
            
            if not field in allowed_fields:  # noqa: E713
                 continue

            if await HeaderPostsService._handle_coordinates_update(
                tracked_changes, source, header.id, header, field, old_value, new_value
            ):
                continue  # Skip if coordinates were updated
            
            if await HeaderPostsService._handle_address_update(
                tracked_changes, source, header.id, header, field, old_value, new_value
            ):
                continue  # Skip if address was updated
            
            if old_value != new_value:
                UpdatePost._update_record(
                    header,
                    field,
                    new_value,
                    tracked_changes,
                    header.id,
                    field,
                    old_value,
                    SourceTable.HEADER,
                )
        return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            tracked_changes)
                
    @staticmethod
    async def _handle_coordinates_update(
        tracked_changes: list, 
        source: str,
        header_id: int, 
        header: EventsHeaders, 
        field: str, 
        old_value: List[float], 
        new_value: List[float]
    ) -> bool:
        
        if field != "coordinates":
            return False
        
        status = UpdateStatus.ERROR
        result: InternalResponse = maps_utils.validate_coordinates_format(new_value)
        point = f"{new_value[0]},{new_value[1]}"
        old_address = header.address
        
        if result.status == ResponseStatus.ERROR:
            message = "Invalid coordinates type. Expected <[float, float]>"
            new_value = point
            UpdatePost._append_tracked_change(
                    tracked_changes, status,
                    message, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
            return True
        
        if point == old_value and result.status == ResponseStatus.SUCCESS:
            message = "Unchanged location"
            new_value = point
            UpdatePost._append_tracked_change(
                    tracked_changes, status,
                    message, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
            return True

        result = await maps_utils.fetch_reverse_geocode_data(
            new_value[0], new_value[1]
        )
        new_value = point
        if result.status == ResponseStatus.ERROR:
            UpdatePost._append_tracked_change(
                    tracked_changes, status,
                    result.message, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
            return True

        address = result.message["address"]
        result = HeaderPostsService.update_location(point, address, header)
        if result.status == ResponseStatus.ERROR:
            UpdatePost._append_tracked_change(
                    tracked_changes, status,
                    result.message, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
            return True
        
        #If coordinates change, address can too
        UpdatePost._append_tracked_change(
                    tracked_changes, UpdateStatus.SUCCESS,
                    None, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
        if old_address != address:
            UpdatePost._append_tracked_change(
                        tracked_changes, UpdateStatus.SUCCESS,
                        None, header_id, header.id,
                        "address", old_address, address,
                        source,
                    )
        return True
    
    @staticmethod
    async def _handle_address_update(
        tracked_changes: list, 
        source: str,
        header_id: int, 
        header: EventsHeaders, 
        field: str, 
        old_value: List[float], 
        new_value: List[float]
    ):
        status = UpdateStatus.ERROR
        old_point = header.coordinates
        
        if field != "address":
            return False
        
        if not isinstance(new_value, str):
            message = "Invalid address type. Expected <str>"
            UpdatePost._append_tracked_change(
                tracked_changes, UpdateStatus.ERROR,
                message, header_id, header.id,
                field, old_value, new_value,
                source,
            )
            return True

        if new_value == old_value:
            message = "Unchanged location"
            UpdatePost._append_tracked_change(
                tracked_changes, UpdateStatus.ERROR,
                message, header_id, header.id,
                field, old_value, new_value,
                source,
            )
            return True

        result: InternalResponse = await maps_utils.fetch_geocode_data(new_value)
        if result.status == ResponseStatus.ERROR:
            UpdatePost._append_tracked_change(
                tracked_changes, UpdateStatus.ERROR,
                result.message, header_id, header.id,
                field, old_value, new_value,
                source,
            )
            return True

        point, address = result.message["point"], result.message["address"]
        point = f"{point[0]},{point[1]}"
        result = HeaderPostsService.update_location(point, address, header)
        if result.status == ResponseStatus.ERROR:
            UpdatePost._append_tracked_change(
                    tracked_changes, status,
                    result.message, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
            return True
        
        #If address change, coordinates can too
        UpdatePost._append_tracked_change(
                    tracked_changes, UpdateStatus.SUCCESS,
                    None, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
        if old_point != point:
            UpdatePost._append_tracked_change(
                        tracked_changes, UpdateStatus.SUCCESS,
                        None, header_id, header.id,
                        "coordinates", old_point, point,
                        source,
                    )
        return True

    @staticmethod
    def update_location(
        point: str, 
        address: str, 
        header: EventsHeaders) -> InternalResponse:
        
        origin = inspect.stack()[0].function
        status = ResponseStatus.SUCCESS
        
        setattr(header, "address", address)
        setattr(header, "coordinates", point)
        setattr(
            header,
            "geom",
            func.ST_SetSRID(func.ST_Point(point[1], point[0]), 4326),
        )
        return SystemResponse.internal_response(status, origin, header)

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

class UpdatePost:
    @staticmethod
    async def update_post_data(
        db: Session, 
        user_id: int, 
        update_data: UpdatePostInput
        ) -> InternalResponse:
        
        origin = inspect.stack()[0].function
        
        for item in update_data.tables:
            if item.table == 0:
                source = SourceTable.HEADER
                update_header: InternalResponse = await HeaderPostsService._update_header(
                    db, source, user_id, item.table, item.changes
                )
                if update_header.status == ResponseStatus.ERROR:
                    return update_header
            # elif item.table == 1:
            #     source = SourceTable.LINES
            #     update_lines: InternalResponse = await EventUpdateService._update_lines(
            #         db, source, user_id, item.table, item.changes
            #     )
            #     if update_lines.status == ResponseStatus.ERROR:
            #         return update_lines
            # elif item.table == 2:
            #     source = SourceTable.RATES
            #     update_rates: InternalResponse = await EventUpdateService._update_rates(
            #         db, source, user_id, item.table, item.changes
            #     )
            #     if update_rates.status == ResponseStatus.ERROR:
            #         return update_rates
            if item.table > 2:
                return SystemResponse.internal_response(
                ResponseStatus.ERROR,
                origin, 
                f"Invalid table specified for {SourceTable.HEADER.value}")
        
        #update_details = (update_header, update_lines, update_rates)
        update_header = update_header.message
        update_details = (update_header)
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, update_details)
    
    @staticmethod
    def _append_tracked_change(
        tracked_changes: list, status: str,
        message: str, record_id: int,
        header_id: int, field: str,
        old_value: any, new_value: any,
        origin: str,
    ):
        """
        Helper function to track all update changes

        Args:
            tracked_changes (list): List to store all history changes
            status (str): Status of the change (Success/Error)
            message (str): _description_
            record_id (int): _description_
            header_id (int): _description_
            field (str): _description_
            old_value (any): _description_
            new_value (any): _description_
            origin (str): _description_
        """
        tracked_changes.append(
            {
                "status": status,
                "origin": origin,
                "message": message,
                "header_id": header_id,
                "record_id": record_id,
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
            }
        )
    
    @staticmethod
    def _update_record(
        fetched_record,
        field,
        new_value,
        tracked_changes,
        row_id,
        field_name,
        old_value,
        origin,
    ):
        setattr(fetched_record, field, new_value)
        UpdatePost._append_tracked_change(
            tracked_changes,
            UpdateStatus.SUCCESS,
            None,
            row_id,
            fetched_record.id,
            field_name,
            old_value,
            new_value,
            origin,
        )

class EventUpdateService:

    @staticmethod
    async def _update_lines(
        db: Session, user_id: int, table: int, changes: UpdateChanges = None
    ):
        """
        Update lines rows
        """
        if not changes:
            return {"status": "error", "details": "No changes to apply in lines"}

        if table != 1:
            return {"status": "error", "details": "Invalid table specified for lines"}

        row_ids = [item.id for item in changes]
        updates = [
            {
                "id": item.id,
                "updates": [
                    {"field": update.field, "value": update.value}
                    for update in item.update
                ],
            }
            for item in changes
        ]

        fetched_header = (
            db.query(EventsHeaders)
            .join(EventsLines, EventsLines.header_id == EventsHeaders.id)
            .filter(EventsLines.id.in_(row_ids), EventsHeaders.owner_id == user_id)
            .first()
        )

        if not fetched_header:
            return {"status": "error", "details": "Unauthorized user"}

        fetched_records = (
            db.query(EventsLines)
            .filter(
                and_(
                    EventsLines.header_id == fetched_header.id,
                    EventsLines.id.in_(row_ids),
                )
            )
            .all()
        )
        if not fetched_records:
            return {"status": "error", "details": "Records not found"}

        tracked_changes = []

        for item in fetched_records:
            record_update = next((u for u in updates if u["id"] == item.id), None)

            if not record_update:
                continue

            for update in record_update["updates"]:
                field = update["field"]
                new_value = update["value"]
                old_value = getattr(item, field, None)

                if isinstance(old_value, datetime) and time_utils.is_valid_datetime(
                    new_value
                ):
                    new_value = datetime.strptime(new_value, "%Y-%m-%d %H:%M:%S.%f")

                    if field == "start" and new_value > item.end:
                        EventUpdateService.append_tracked_change(
                            tracked_changes,
                            "error",
                            f"Starting date must be before {item.end}",
                            item.id,
                            fetched_header.id,
                            field,
                            old_value,
                            new_value,
                            "lines",
                        )
                        continue  # Skip item

                    if field == "end" and new_value < item.start:
                        EventUpdateService.append_tracked_change(
                            tracked_changes,
                            "error",
                            f"Ending date must be after {item.start}",
                            item.id,
                            fetched_header.id,
                            field,
                            old_value,
                            new_value,
                            "lines",
                        )
                        continue  # Skip item

                if old_value != new_value:
                    EventUpdateService.append_tracked_change(
                        tracked_changes,
                        "success",
                        None,
                        item.id,
                        fetched_header.id,
                        field,
                        old_value,
                        new_value,
                        "lines",
                    )
                    setattr(item, field, new_value)

        db.commit()

        return (
            {"status": "success", "details": tracked_changes}
            if len(tracked_changes) > 0
            else {"status": "error", "details": "No changes applied in lines"}
        )

    @staticmethod
    async def _update_rates(
        db: Session, user_id: int, table: int, changes: UpdateChanges = None
    ):
        """
        Update rates rows
        """
        if not changes:
            return {"status": "error", "details": "No changes to apply in rates"}

        if table != 2:
            return {"status": "error", "details": "Invalid table specified for rates"}

        row_ids = [item.id for item in changes]
        updates = [
            {
                "id": item.id,
                "updates": [
                    {"field": update.field, "value": update.value}
                    for update in item.update
                ],
            }
            for item in changes
        ]

        fetched_ids = (
            db.query(EventsHeaders.id, EventsLines.id)
            .join(EventsLines, EventsLines.header_id == EventsHeaders.id)
            .join(Rates, Rates.line_id == EventsLines.id)
            .filter(Rates.id.in_(row_ids), EventsHeaders.owner_id == user_id)
            .all()
        )

        if not fetched_ids:
            return {"status": "error", "details": "Unauthorized user for rates"}

        header_ids, lines_id = [item[0] for item in fetched_ids], [
            item[1] for item in fetched_ids
        ]
        header_ids, lines_id = list(set(header_ids)), set(lines_id)
        header_ids = header_ids[0] if len(header_ids) == 1 else header_ids

        fetched_records = (
            db.query(Rates)
            .filter(and_(Rates.line_id.in_(lines_id), Rates.id.in_(row_ids)))
            .all()
        )
        if not fetched_records:
            return {"status": "error", "details": "Records not found in rates"}

        tracked_changes = []

        for item in fetched_records:
            record_update = next((u for u in updates if u["id"] == item.id), None)

            if not record_update:
                continue

            for update in record_update["updates"]:
                field = update["field"]
                new_value = update["value"]
                old_value = getattr(item, field, None)

                if old_value != new_value:
                    EventUpdateService.append_tracked_change(
                        tracked_changes,
                        "success",
                        None,
                        item.id,
                        header_ids,
                        field,
                        old_value,
                        new_value,
                        "rate",
                    )
                    setattr(item, field, new_value)

        db.commit()

        return (
            {"status": "success", "details": tracked_changes}
            if len(tracked_changes) > 0
            else {"status": "error", "details": "No changes applied in rates"}
        )

    @staticmethod
    def group_changes_by_event(changes):
        relevant_changes = []
        for item in changes.get("details", []):
            if item.get("status") != "error":
                for change in item.get("details", []):
                    header_id = change.get("header_id")
                    origin = change.get("origin")
                    field = change.get("field")
                    old_value = change.get("old_value")
                    new_value = change.get("new_value")
                    record_id = change.get("record_id")

                    header_entry = next(
                        (entry for entry in relevant_changes if header_id in entry),
                        None,
                    )
                    if not header_entry:
                        header_entry = {header_id: {"header": [], "lines": {}}}
                        relevant_changes.append(header_entry)

                    header_data = header_entry[header_id]

                    if origin == "header":
                        header_data["header"].append(
                            {
                                "field": field,
                                "old_value": old_value,
                                "new_value": new_value,
                            }
                        )
                    elif origin == "lines":
                        if record_id not in header_data["lines"]:
                            header_data["lines"][record_id] = {
                                "fields": [],
                                "rates": [],
                            }
                        header_data["lines"][record_id]["fields"].append(
                            {
                                "field": field,
                                "old_value": old_value,
                                "new_value": new_value,
                            }
                        )
                    elif origin == "rate":
                        if record_id not in header_data["lines"]:
                            header_data["lines"][record_id] = {
                                "fields": [],
                                "rates": [],
                            }
                        header_data["lines"][record_id]["rates"].append(
                            {
                                "rate_id": record_id,
                                "field": field,
                                "old_value": old_value,
                                "new_value": new_value,
                            }
                        )
        return relevant_changes
