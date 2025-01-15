from enum import IntEnum, Enum
from functools import wraps

from app.responses import SystemResponse, InternalResponse
from app.schemas import ResponseStatus, UpdateChanges
import inspect

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from typing import List

from datetime import datetime, timezone
from app.models import Categories, EventsHeaders, EventsLines, Rates
from app.schemas import (
    NewPostHeaderInput, 
    NewPostLinesInput, 
    EventLines, 
    UpdatePostInput,
    UpdatePostConfirmInput)
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
                continue
            
            if await HeaderPostsService._handle_address_update(
                tracked_changes, source, header.id, header, field, old_value, new_value
            ):
                continue
            
            if old_value != new_value:
                UpdatePost._track_changes(
                    tracked_changes,
                    UpdateStatus.SUCCESS,
                    None,
                    header.id,
                    header.id,
                    field,
                    old_value,
                    new_value,
                    source,
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
            UpdatePost._track_changes(
                    tracked_changes, status,
                    message, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
            return True
        
        if point == old_value and result.status == ResponseStatus.SUCCESS:
            message = "Unchanged location"
            new_value = point
            UpdatePost._track_changes(
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
            UpdatePost._track_changes(
                    tracked_changes, status,
                    result.message, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
            return True

        address = result.message["address"]
        
        #If coordinates change, address can too
        UpdatePost._track_changes(
                    tracked_changes, UpdateStatus.SUCCESS,
                    None, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
        if old_address != address:
            UpdatePost._track_changes(
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
            UpdatePost._track_changes(
                tracked_changes, UpdateStatus.ERROR,
                message, header_id, header.id,
                field, old_value, new_value,
                source,
            )
            return True

        if new_value == old_value:
            message = "Unchanged location"
            UpdatePost._track_changes(
                tracked_changes, UpdateStatus.ERROR,
                message, header_id, header.id,
                field, old_value, new_value,
                source,
            )
            return True

        result: InternalResponse = await maps_utils.fetch_geocode_data(new_value)
        if result.status == ResponseStatus.ERROR:
            UpdatePost._track_changes(
                tracked_changes, UpdateStatus.ERROR,
                result.message, header_id, header.id,
                field, old_value, new_value,
                source,
            )
            return True

        point, _ = result.message["point"], result.message["address"]
        point = f"{point[0]},{point[1]}"
        
        #If address change, coordinates can too
        UpdatePost._track_changes(
                    tracked_changes, UpdateStatus.SUCCESS,
                    None, header_id, header.id,
                    field, old_value, new_value,
                    source,
                )
        if old_point != point:
            UpdatePost._track_changes(
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
    
    async def _update_lines(
        db: Session, 
        source: str,
        user_id: int, 
        table: int, 
        changes: UpdateChanges = None
    ) -> InternalResponse:
        
        origin = inspect.stack()[0].function
        status = ResponseStatus.ERROR
        
        if not changes:
            message = "No changes applied to lines"
            return SystemResponse.internal_response(
                status, origin, message)

        if table != 1:
            message = "Invalid table specified for lines"
            return SystemResponse.internal_response(
                status, origin, message)

        lines_ids = [item.id for item in changes]
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

        result: InternalResponse = fetch_data_utils.get_header_from_lines(db, user_id, lines_ids)
        if result.status == ResponseStatus.ERROR:
            message = "Unauthorized user"
            return SystemResponse.internal_response(
                status, origin, message)
            
        header: EventsHeaders = result.message
        result = fetch_data_utils.get_selected_lines_from_same_header(db, header.id, lines_ids)
        if result.status == ResponseStatus.ERROR:
            message = "Lines not found"
            return SystemResponse.internal_response(
                status, origin, message)
        
        lines = result.message
        tracked_changes = []
        allowed_lines_fields = ["start", "end", "isPublic", "capacity"]

        for item in lines:
            
            record_update = next((u for u in updates if u["id"] == item.id), None)
            if not record_update:
                continue
            
            new_dates_references = None
            check_for_fields = {"start", "end"}
            fields_to_update = {d['field'] for d in record_update["updates"] if 'field' in d}
            found_both_dates_to_update = check_for_fields.issubset(fields_to_update)
            
            if found_both_dates_to_update:
                new_dates_references = {d['field']: d['value'] for d in record_update["updates"] if d['field'] in check_for_fields}
                result: InternalResponse = time_utils.convert_string_to_utc(new_dates_references["start"])
                if result.status == ResponseStatus.ERROR:
                    continue
                new_dates_references["start"] = result.message
                result: InternalResponse = time_utils.convert_string_to_utc(new_dates_references["end"])
                if result.status == ResponseStatus.ERROR:
                    continue
                new_dates_references["end"] = result.message

            for update in record_update["updates"]:
                field = update["field"]
                new_value = update["value"]
                old_value = getattr(item, field, None)
                
                if not field in allowed_lines_fields:  # noqa: E713
                    continue

                if isinstance(old_value, datetime) and time_utils.is_valid_date(new_value):
                    result: InternalResponse = time_utils.convert_string_to_utc(new_value)
                    if result.status == ResponseStatus.ERROR:
                        continue
                    new_value = result.message

                    if found_both_dates_to_update and new_dates_references:
                        if field == "start" and new_value > new_dates_references['end']:
                            message = f"Starting date must be before ending date {new_dates_references['end']}"
                            UpdatePost._track_changes(
                                tracked_changes,
                                UpdateStatus.ERROR,
                                message,
                                item.id,
                                header.id,
                                field,
                                old_value,
                                new_value,
                                source,
                            )
                            continue
                        if field == "end" and new_value < new_dates_references['start']:
                            message = f"Ending date must be after starting date {new_dates_references['start']}"
                            UpdatePost._track_changes(
                                tracked_changes,
                                UpdateStatus.ERROR,
                                message,
                                item.id,
                                header.id,
                                field,
                                old_value,
                                new_value,
                                source,
                            )
                            continue
                    else:
                        if field == "start" and new_value > item.end:
                            message = f"Starting date must be before ending date {item.end}"
                            UpdatePost._track_changes(
                                tracked_changes,
                                UpdateStatus.ERROR,
                                message,
                                item.id,
                                header.id,
                                field,
                                old_value,
                                new_value,
                                source,
                            )
                            continue
                        if field == "end" and new_value < item.start:
                            message = f"Ending date must be after starting date {item.start}"
                            UpdatePost._track_changes(
                                tracked_changes,
                                UpdateStatus.ERROR,
                                message,
                                item.id,
                                header.id,
                                field,
                                old_value,
                                new_value,
                                source,
                            )
                            continue

                if old_value != new_value:
                    UpdatePost._track_changes(
                        tracked_changes,
                        UpdateStatus.SUCCESS,
                        None,
                        item.id,
                        header.id,
                        field,
                        old_value,
                        new_value,
                        source,
                    )

        message = f"No changes applied in {SourceTable.LINES.value}"
        if len(tracked_changes) > 0:
            message = tracked_changes
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, message)

class RatesPostService:
    async def _update_rates(
        db: Session,
        source: str, 
        user_id: int, 
        table: int, 
        changes: UpdateChanges = None
    ) -> InternalResponse:
        
        origin = inspect.stack()[0].function
        
        if not changes:
            message = f"No changes to apply in {SourceTable.RATES.value}"
            return SystemResponse.internal_response(
                ResponseStatus.SUCCESS, 
                origin, 
                message)

        if table != 2:
            message = f"Invalid table specified for {SourceTable.RATES.value}"
            return SystemResponse.internal_response(
                ResponseStatus.SUCCESS, 
                origin, 
                message)

        rates_ids = [item.id for item in changes]
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

        result: InternalResponse = fetch_data_utils.get_header_and_lines_from_rates(db, user_id, rates_ids)
        if result.status == ResponseStatus.ERROR:
            message = f"Unauthorized user for {SourceTable.RATES.value}"
            return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            message)
            
        header_and_lines_ids: EventsHeaders = result.message
        header_ids, lines_id = [item[0] for item in header_and_lines_ids], [
            item[1] for item in header_and_lines_ids
        ]
        header_ids, lines_id = list(set(header_ids)), set(lines_id)
        header_ids = header_ids[0] if len(header_ids) == 1 else header_ids

        
        result: InternalResponse = fetch_data_utils.get_selected_rates_from_same_lines(db, rates_ids, lines_id)
        if result.status == ResponseStatus.ERROR:
            message = f"Records not found in {SourceTable.RATES.value}"
            return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            message)
            
        tracked_changes = []
        rates = result.message
        allowed_rates_fields = ["title", "amount", "currency"]

        for item in rates:
            record_update = next((u for u in updates if u["id"] == item.id), None)

            if not record_update:
                continue

            for update in record_update["updates"]:
                field = update["field"]
                new_value = update["value"]
                old_value = getattr(item, field, None)
                
                if not field in allowed_rates_fields:  # noqa: E713
                    continue

                if old_value != new_value:
                    UpdatePost._track_changes(
                        tracked_changes,
                        UpdateStatus.SUCCESS,
                        None,
                        item.id,
                        header_ids,
                        field,
                        old_value,
                        new_value,
                        source,
                    )
                    
        message = f"No changes applied to {SourceTable.RATES.value}"
        if len(tracked_changes) > 0:
            message = tracked_changes
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, message)
                   
class PostConfirmation:
    def update_db(
        db: Session,
        user_id: int, 
        updates: List[UpdatePostConfirmInput]) -> InternalResponse:
        #TODO: REFACTOR
        
        origin = inspect.stack()[0].function
        status = ResponseStatus.ERROR
        
        if not isinstance(updates, list) or len(updates) != 3:
            message = "Invalid input"
            return SystemResponse.internal_response(status, origin, message)
        
        header_updates, lines_updates, rates_updates = [], [], []
        header_id = -1
        
        for index, table in enumerate(updates, start = 0):
            
            if index == 0:
                for item in table:
                    if item.status != UpdateStatus.SUCCESS.value:
                        continue
                    update = (item.source, item.header_id, item.record_id, item.field, item.old_value, item.new_value)
                    update_dict = PostConfirmation._build_dict_structure(update)
                    header_updates.append(update_dict)
            
            elif index == 1:
                for item in table:
                    if item.status != UpdateStatus.SUCCESS.value:
                        continue
                    if header_id == -1:
                        header_id = item.header_id
                    update = (item.source, item.header_id, item.record_id, item.field, item.old_value, item.new_value)
                    update_dict = PostConfirmation._build_dict_structure(update)
                    lines_updates.append(update_dict)
            
            elif index == 2:
                for item in table:
                    if item.status != UpdateStatus.SUCCESS.value:
                        continue
                    update = (item.source, item.header_id, item.record_id, item.field, item.old_value, item.new_value)
                    update_dict = PostConfirmation._build_dict_structure(update)
                    rates_updates.append(update_dict)
            
            else:
                continue
            
        header_ids, lines_ids, rates_ids = PostConfirmation._get_ids(header_updates,
                                                                     lines_updates, 
                                                                     rates_updates)
        if header_ids:
            result: InternalResponse = fetch_data_utils.get_header(db, user_id, header_ids)
            if result.status == ResponseStatus.ERROR:
                return result
            header: EventsHeaders = result.message[0]
            
            for item in header_updates:
                if item["field"] == "coordinates" and isinstance(item["new_value"], list):
                    coord_to_str = f"{item['new_value'][0]},{item['new_value'][1]}"
                    setattr(header, item["field"], coord_to_str)
                else:
                    setattr(header, item["field"], item["new_value"])
            
            result = fetch_data_utils.update_db(db, header)
            if result.status == ResponseStatus.ERROR:
                return result
                
        if lines_ids:
            result: InternalResponse = fetch_data_utils.get_selected_lines_from_same_header(db, header_id, lines_ids)
            if result.status == ResponseStatus.ERROR:
                return result
            lines: List[EventLines] = result.message
            
            for item in lines_updates:
                for line in lines:
                    if item["record_id"] == line.id:
                        setattr(line, item["field"], item["new_value"])
                        continue
            for line in lines:
                result = fetch_data_utils.update_db(db, line)
                if result.status == ResponseStatus.ERROR:
                    return result
        
        if rates_ids:
            result: InternalResponse = fetch_data_utils.get_header_and_lines_from_rates(db, user_id, rates_ids)
            if result.status == ResponseStatus.ERROR:
                return result
            lines_ids = [d[1] for d in result.message]
            result: InternalResponse = fetch_data_utils.get_selected_rates_from_same_lines(db, rates_ids, lines_ids)
            if result.status == ResponseStatus.ERROR:
                return result
            rates: List[Rates] = result.message
            
            for item in rates_updates:
                for rate in rates:
                    if item["record_id"] == rate.id:
                        setattr(rate, item["field"], item["new_value"])
                        continue
            for rate in rates:
                result = fetch_data_utils.update_db(db, rate)
                if result.status == ResponseStatus.ERROR:
                    return result
            
        return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            (header_updates, lines_updates, rates_updates))
    
    def _build_dict_structure(updates: list) -> dict:
        return {
            "source": updates[0],
            "header_id": updates[1], 
            "record_id": updates[2], 
            "field": updates[3],
            "old_value": updates[4],
            "new_value": updates[5]
            }
    
    def _get_ids(
        header_updates: list, 
        lines_updates: list, 
        rates_updates: list) -> tuple:
        
        header_ids, lines_ids, rates_ids = [], [], []
        
        header_ids.extend(item["record_id"] for item in header_updates if item["record_id"] not in header_ids)
        lines_ids.extend(item["record_id"] for item in lines_updates if item["record_id"] not in lines_ids)
        rates_ids.extend(item["record_id"] for item in rates_updates if item["record_id"] not in rates_ids)
        
        return (header_ids, lines_ids, rates_ids)
    
    @staticmethod
    def build_post_updates_structure(tables: list) -> InternalResponse:
        origin = inspect.stack()[0].function
        
        relevant_changes = []

        for table in tables:
            for change in table:
                header_id = change["header_id"]
                record_id = change["record_id"]
                source = change["source"]
                field = change["field"]
                old_value = change["old_value"]
                new_value = change["new_value"]
                
                header_entry = next(
                    (entry for entry in relevant_changes if header_id in entry), None
                )
                if not header_entry:
                    header_entry = {header_id: {SourceTable.HEADER.value: [], SourceTable.LINES.value: {}}}
                    relevant_changes.append(header_entry)

                header_data = header_entry[header_id]

                if source == SourceTable.HEADER.value:
                    header_data[SourceTable.HEADER.value].append(
                        {
                            "field": field,
                            "old_value": old_value,
                            "new_value": new_value,
                        }
                    )
                elif source == SourceTable.LINES.value:
                    if record_id not in header_data[SourceTable.LINES.value]:
                        header_data[SourceTable.LINES.value][record_id] = {"fields": [], SourceTable.RATES.value: []}
                    header_data[SourceTable.LINES.value][record_id]["fields"].append(
                        {
                            "field": field,
                            "old_value": old_value,
                            "new_value": new_value,
                        }
                    )
                elif source == SourceTable.RATES.value:
                    if record_id not in header_data[SourceTable.LINES.value]:
                        header_data[SourceTable.LINES.value][record_id] = {"fields": [], SourceTable.RATES.value: []}
                    header_data[SourceTable.LINES.value][record_id][SourceTable.RATES.value].append(
                        {
                            "rate_id": record_id,
                            "field": field,
                            "old_value": old_value,
                            "new_value": new_value,
                        }
                    )
                    
        return SystemResponse.internal_response(
                ResponseStatus.SUCCESS, 
                origin, 
                relevant_changes)


class UpdatePost:
    @staticmethod
    async def update_post_data(
        db: Session, 
        user_id: int, 
        update_data: UpdatePostInput
        ) -> InternalResponse:
        
        origin = inspect.stack()[0].function
        update_header, update_lines, update_rates = [], [], []
        
        for item in update_data.tables:
            
            if item.table == 0:
                source = SourceTable.HEADER
                header_result: InternalResponse = await HeaderPostsService._update_header(
                    db, source, user_id, item.table, item.changes
                )
                if header_result.status == ResponseStatus.ERROR:
                    return header_result
                update_header = header_result.message
                
            elif item.table == 1:
                source = SourceTable.LINES
                lines_result: InternalResponse = await LinesPostService._update_lines(
                    db, source, user_id, item.table, item.changes
                )
                if lines_result.status == ResponseStatus.ERROR:
                    return lines_result
                update_lines = lines_result.message
                
            elif item.table == 2:
                source = SourceTable.RATES
                result_rates: InternalResponse = await RatesPostService._update_rates(
                    db, source, user_id, item.table, item.changes
                )
                if result_rates.status == ResponseStatus.ERROR:
                    return result_rates
                update_rates = result_rates.message
            
            if item.table > 2:
                return SystemResponse.internal_response(
                ResponseStatus.ERROR,
                origin, 
                "Invalid specified source table")

        update_details = (update_header, update_lines, update_rates)
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, update_details)
    
    @staticmethod
    def _track_changes(
        tracked_changes: list, status: str,
        message: str, record_id: int,
        header_id: int, field: str,
        old_value: any, new_value: any,
        source: str,
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
            source (str): _description_
        """
        tracked_changes.append(
            {
                "status": status,
                "source": source,
                "message": message,
                "header_id": header_id,
                "record_id": record_id,
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
            }
        )