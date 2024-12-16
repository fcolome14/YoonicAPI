from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Union
from app.models import EventsLines, EventsHeaders, Rates
from app.schemas import NewPostInput, RateDetails
from app.schemas.bases import UpdateChanges
from app.services.repeater_service import select_repeater, select_repeater_custom
from app.services.rate_service import RateService, pack_rates
from app.utils import utils, time_utils, maps_utils
from datetime import datetime

class EventService:
    @staticmethod
    def generate_post_lines(db: Session, posting_data: NewPostInput, header_id: int):
        if posting_data.custom_option_selected:
            return EventService._custom_mode(db, posting_data, header_id)
        
        if isinstance(posting_data.line, List):
            return {"status":"error", "details": "Lines can't be <List>, expected single object"}
        
        if posting_data.repeat:
            return EventService._handle_repeated_lines(db, posting_data, header_id)
        
        return EventService._handle_single_line(db, posting_data, header_id)
    
    @staticmethod
    def _handle_single_line(db: Session, posting_data: NewPostInput, header_id: int):
        line = EventsLines(
            header_id=header_id,
            start=posting_data.line.start,
            end=posting_data.line.end,
            capacity=posting_data.line.capacity,
            isPublic=posting_data.line.isPublic
        )
        db.add(line)
        db.commit()
        db.refresh(line)
        
        rates_dict, ids_dict = pack_rates(posting_data, [line])
        RateService.add_rates(posting_data, db, rates_dict, ids_dict)
        return {"status": "success", "details": "Event created"}
    
    @staticmethod
    def _handle_repeated_lines(db: Session, posting_data: NewPostInput, header_id: int):
        repeats_dict = select_repeater(
            every=posting_data.when_to,
            start=posting_data.line.start,
            end=posting_data.line.end,
            occurrences=posting_data.occurrences
        )
        if isinstance(repeats_dict, dict) and repeats_dict.get("status") == "error":  # Handle error
            return {"status": "error", "details": repeats_dict.get("details")}
            
        lines = [
            EventsLines(
                header_id=header_id,
                start=event[0],
                end=event[1],
                capacity=posting_data.line.capacity,
                isPublic=posting_data.line.isPublic
            )
            for repeat in repeats_dict.values()
            for event in repeat
        ]
        db.add_all(lines)
        db.commit()
        for line in lines:
            db.refresh(line)
        
        rates_dict, ids_dict = pack_rates(posting_data, lines)
        RateService.add_rates(posting_data, db, rates_dict, ids_dict)
        return {"status": "success", "details": "Event created"}
    
    @staticmethod
    def _custom_mode(db: Session, posting_data: NewPostInput, header_id: int):
        if posting_data.custom_each_day:
            return EventService._handle_custom_each_day(db, posting_data, header_id)

        if isinstance(posting_data.line, List):
            return {"status": "error", "details": "Unexpected List type for 'line'"}
        
        return EventService._handle_custom_week_days(db, posting_data, header_id)

    @staticmethod
    def _handle_custom_each_day(db: Session, posting_data: NewPostInput, header_id: int):
        """
        Handles custom mode for events occurring on each day with repetitions.
        """
        if not isinstance(posting_data.line, List):
            return {"status": "error", "details": "Line data must be a list in custom_each_day mode"}

        if posting_data.repeat:
            repeats_dict, payload = EventService._prepare_repeats_and_payload(posting_data)
            if isinstance(repeats_dict, dict) and repeats_dict.get("status") == "error":
                return {"status": "error", "details": repeats_dict.get("details")}
            
            lines = EventService._create_event_lines(header_id, repeats_dict, payload)
            return EventService._finalize_lines(db, posting_data, lines)
        
        days_dict, payload = EventService._prepare_lines_and_payload(posting_data)
        lines = [
                EventsLines(
                    header_id=header_id,
                    start=day[0],
                    end=day[1],
                    capacity=data[0],
                    isPublic=data[1]
                )
                for day, data in zip(days_dict.values(), payload.values())
        ]
        return EventService._finalize_lines(db, posting_data, lines)

    @staticmethod
    def _handle_custom_week_days(db: Session, posting_data: NewPostInput, header_id: int):
        """
        Handles custom mode for events scheduled for specific weekdays.
        """
        week_days = time_utils.set_week_days(
            start=posting_data.line.start, 
            end=posting_data.line.end, 
            target_days=posting_data.for_days
        )

        if posting_data.repeat:
            start, end = utils.split_dict_to_array(week_days)
            repeats_dict = select_repeater_custom(
                every=posting_data.when_to, 
                start=start, 
                end=end, 
                occurrences=posting_data.occurrences
            )
            if isinstance(repeats_dict, dict) and repeats_dict.get("status") == "error":
                return {"status": "error", "details": repeats_dict.get("details")}

            lines = [
                EventsLines(
                    header_id=header_id,
                    start=event[0],
                    end=event[1],
                    capacity=posting_data.line.capacity,
                    isPublic=posting_data.line.isPublic
                )
                for repeat in repeats_dict.values()
                for event in repeat
            ]
            return EventService._finalize_lines(db, posting_data, lines)
        
        lines = [
                EventsLines(
                    header_id=header_id,
                    start=day[0],
                    end=day[1],
                    capacity=posting_data.line.capacity,
                    isPublic=posting_data.line.isPublic
                )
                for event in week_days.values()
                for day in event
            ]
        return EventService._finalize_lines(db, posting_data, lines)

    @staticmethod
    def _create_event_lines(header_id: int, repeats: dict, payload: dict):
        """
        Creates event lines based on repeat intervals and payload.
        """
        return [
            EventsLines(
                header_id=header_id,
                start=day[0],
                end=day[1],
                capacity=data[0],
                isPublic=data[1]
            )
            for event, data in zip(repeats.values(), payload.values())
            for day in event
        ]

    @staticmethod
    def _finalize_lines(db: Session, posting_data: Union[List[RateDetails], RateDetails], lines_db: List[EventsLines]):
        """
        Finalizes the event lines by refreshing and querying their IDs.
        """
        db.add_all(lines_db)
        db.commit()
        for line in lines_db:
            db.refresh(line)

        rates_dict, ids_dict = pack_rates(posting_data, lines_db)
        RateService.add_rates(posting_data, db, rates_dict, ids_dict)
        return {"status": "success", "details": "Event created"}

    @staticmethod
    def _prepare_repeats_and_payload(posting_data: NewPostInput):
        """
        Prepares repeat intervals and payload for event lines.
        """
        start, end = zip(*[(item.start, item.end) for item in posting_data.line])
        
        repeats = select_repeater_custom(
            every=posting_data.when_to,
            start=start,
            end=end,
            occurrences=posting_data.occurrences
        )
        
        if isinstance(repeats, dict) and repeats.get("status") == "error":
            return {"status": "error", "details": repeats.get("details")}
        
        payload_dict = {
            index: (day.capacity, day.isPublic)
            for index, day in enumerate(posting_data.line)
        }
        
        return repeats, payload_dict

    @staticmethod
    def _prepare_lines_and_payload(posting_data: NewPostInput):
        """
        Prepares repeat intervals and payload for event lines.
        """
        return {
            index: (day.start, day.end) for index, day in enumerate(posting_data.line)
        }, {
            index: (day.capacity, day.isPublic) for index, day in enumerate(posting_data.line)
        }



class EventUpdateService:
    
    @staticmethod
    async def _update_header(db: Session, user_id: int, table: int, changes: UpdateChanges = None):
        """
        Update header row
        """
        if not changes:
            return {"status": "error", "details": "No changes to apply in header"}

        if table != 0:
            return {"status": "error", "details": "Invalid table specified for header"}

        row, updates = [item.id for item in changes], [item.update for item in changes]
        fetched_record = db.query(EventsHeaders).filter(and_(EventsHeaders.owner_id == user_id, EventsHeaders.id == row[0])).first()
        
        if not fetched_record:
            return {"status": "error", "details": "Record not found in header"}

        tracked_changes = []

        for update in updates[0]:
            field = update.field
            new_value = update.value
            old_value = getattr(fetched_record, field, None)

            if await EventUpdateService._handle_coordinates_update(tracked_changes, row[0], fetched_record, field, old_value, new_value):
                continue  # Skip if coordinates were updated
            if await EventUpdateService._handle_address_update(tracked_changes, row[0], fetched_record, field, old_value, new_value):
                continue  # Skip if address was updated

            if old_value != new_value:
                EventUpdateService._update_record(fetched_record, field, new_value, tracked_changes, row[0], field, old_value, "header")

        db.commit()
        return {"status": "success", "details": tracked_changes} if len(tracked_changes) > 0 else {"status": "error", "details": "No changes applied in header"}


    @staticmethod
    async def _handle_coordinates_update(tracked_changes, row_id, fetched_record, field, old_value, new_value):
        if field == "coordinates":
            if not EventUpdateService._is_valid_coordinates(new_value):
                EventUpdateService.append_tracked_change(tracked_changes, "error", "Invalid coordinates type. Expected <[float, float]>", row_id, fetched_record.id, field, old_value, new_value, "header")
                return True
            
            if f'{new_value[0]},{new_value[1]}' == old_value:
                EventUpdateService.append_tracked_change(tracked_changes, "error", "Unchanged location", row_id, fetched_record.id, field, old_value, new_value, "header")
                return True

            result = await maps_utils.fetch_reverse_geocode_data(new_value[0], new_value[1])
            if result.get("status") == "error":
                EventUpdateService.append_tracked_change(tracked_changes, "error", result.get("details"), row_id, fetched_record.id, field, old_value, new_value, "header")
                return True
            
            point = result.get("point")
            setattr(fetched_record, "address", result.get("address"))
            setattr(fetched_record, "coordinates", f'{point[0]},{point[1]}')
            setattr(fetched_record, "geom", func.ST_SetSRID(func.ST_Point(point[1], point[0]), 4326))
            EventUpdateService.append_tracked_change(tracked_changes, "success", None, row_id, fetched_record.id, field, old_value, new_value, "header")
            return True
        return False


    @staticmethod
    async def _handle_address_update(tracked_changes, row_id, fetched_record, field, old_value, new_value):
        if field == "address":
            if not isinstance(new_value, str):
                EventUpdateService.append_tracked_change(tracked_changes, "error", "Invalid address type. Expected <str>", row_id, fetched_record.id, field, old_value, new_value, "header")
                return True
            
            if new_value == old_value:
                EventUpdateService.append_tracked_change(tracked_changes, "error", "Unchanged location", row_id, fetched_record.id, field, old_value, new_value, "header")
                return True

            result = await maps_utils.fetch_geocode_data(new_value)
            if result.get("status") == "error":
                EventUpdateService.append_tracked_change(tracked_changes, "error", result.get("details"), row_id, fetched_record.id, field, old_value, new_value, "header")
                return True

            point = result.get("point")
            setattr(fetched_record, "address", result.get("address"))
            setattr(fetched_record, "coordinates", f'{point[0]},{point[1]}')
            setattr(fetched_record, "geom", func.ST_SetSRID(func.ST_Point(point[1], point[0]), 4326))
            EventUpdateService.append_tracked_change(tracked_changes, "success", None, row_id, fetched_record.id, field, old_value, new_value, "header")
            return True
        return False


    @staticmethod
    def _is_valid_coordinates(coordinates):
        return isinstance(coordinates, tuple) and len(coordinates) == 2 and isinstance(coordinates[0], (float, int)) and isinstance(coordinates[1], (float, int))


    @staticmethod
    def _update_record(fetched_record, field, new_value, tracked_changes, row_id, field_name, old_value, origin):
        setattr(fetched_record, field, new_value)
        EventUpdateService.append_tracked_change(tracked_changes, "success", None, row_id, fetched_record.id, field_name, old_value, new_value, origin)


    @staticmethod
    async def _update_lines(db: Session, user_id: int, table: int, changes: UpdateChanges = None):
        """
        Update lines rows
        """
        if not changes:
            return {"status": "error", "details": "No changes to apply in lines"}
        
        if table != 1:
            return {"status": "error", "details": "Invalid table specified for lines"}

        row_ids = [item.id for item in changes]
        updates = [{"id": item.id, "updates": [{"field": update.field, "value": update.value} for update in item.update]} for item in changes]
        
        fetched_header = db.query(EventsHeaders).join(
            EventsLines, EventsLines.header_id == EventsHeaders.id).filter(
            EventsLines.id.in_(row_ids), EventsHeaders.owner_id == user_id).first()

        if not fetched_header:
            return {"status": "error", "details": "Unauthorized user"}
        
        fetched_records = db.query(EventsLines).filter(and_(EventsLines.header_id == fetched_header.id, EventsLines.id.in_(row_ids))).all()
        if not fetched_records:
            return {"status": "error", "details": "Records not found"}

        tracked_changes = []
        
        for item in fetched_records:
            record_update = next((u for u in updates if u['id'] == item.id), None)
            
            if not record_update:
                continue
            
            for update in record_update['updates']:
                field = update['field']
                new_value = update['value']
                old_value = getattr(item, field, None)

                if isinstance(old_value, datetime) and time_utils.is_valid_datetime(new_value):
                    new_value = datetime.strptime(new_value, "%Y-%m-%d %H:%M:%S.%f")
                    
                    if field == "start" and new_value > item.end:
                        EventUpdateService.append_tracked_change(tracked_changes, "error", f"Starting date must be before {item.end}", item.id, fetched_header.id, field, old_value, new_value, "lines")
                        continue  # Skip item

                    if field == "end" and new_value < item.start:
                        EventUpdateService.append_tracked_change(tracked_changes, "error", f"Ending date must be after {item.start}", item.id, fetched_header.id, field, old_value, new_value, "lines")
                        continue  # Skip item
                
                if old_value != new_value:
                    EventUpdateService.append_tracked_change(tracked_changes, "success", None, item.id, fetched_header.id, field, old_value, new_value, "lines")
                    setattr(item, field, new_value)

        db.commit()

        return {"status": "success", "details": tracked_changes} if len(tracked_changes) > 0 else {"status": "error", "details": "No changes applied in lines"}
    
    @staticmethod
    async def _update_rates(db: Session, user_id: int, table: int, changes: UpdateChanges = None):
        """
        Update rates rows
        """
        if not changes:
            return {"status": "error", "details": "No changes to apply in rates"}
        
        if table != 2:
            return {"status": "error", "details": "Invalid table specified for rates"}

        row_ids = [item.id for item in changes]
        updates = [{"id": item.id, "updates": [{"field": update.field, "value": update.value} for update in item.update]} for item in changes]
        
        fetched_ids = db.query(EventsHeaders.id, EventsLines.id).join(
            EventsLines, EventsLines.header_id == EventsHeaders.id).join(
            Rates, Rates.line_id == EventsLines.id).filter(
            Rates.id.in_(row_ids), EventsHeaders.owner_id == user_id).all()

        if not fetched_ids:
            return {"status": "error", "details": "Unauthorized user for rates"}
        
        header_ids, lines_id = [item[0] for item in fetched_ids], [item[1] for item in fetched_ids]
        header_ids, lines_id = list(set(header_ids)), set(lines_id)
        header_ids = header_ids[0] if len(header_ids) == 1 else header_ids
        
        fetched_records = db.query(Rates).filter(and_(Rates.line_id.in_(lines_id), Rates.id.in_(row_ids))).all()
        if not fetched_records:
            return {"status": "error", "details": "Records not found in rates"}

        tracked_changes = []
        
        for item in fetched_records:
            record_update = next((u for u in updates if u['id'] == item.id), None)
            
            if not record_update:
                continue
            
            for update in record_update['updates']:
                field = update['field']
                new_value = update['value']
                old_value = getattr(item, field, None)
                
                if old_value != new_value:
                    EventUpdateService.append_tracked_change(tracked_changes, "success", None, item.id, header_ids, field, old_value, new_value, "rate")
                    setattr(item, field, new_value)

        db.commit()

        return {"status": "success", "details": tracked_changes} if len(tracked_changes) > 0 else {"status": "error", "details": "No changes applied in rates"}


    @staticmethod
    def append_tracked_change(tracked_changes, status, message, record_id, header_id, field, old_value, new_value, origin):
        """
        Helper function to append a tracked change to the list.
        """
        tracked_changes.append({
            "status": status,
            "origin": origin,
            "message": message,
            "header_id": header_id,
            "record_id": record_id,
            "field": field,
            "old_value": old_value,
            "new_value": new_value
        })
    
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

                    header_entry = next((entry for entry in relevant_changes if header_id in entry), None)
                    if not header_entry:
                        header_entry = {header_id: {"header": [], "lines": {}}}
                        relevant_changes.append(header_entry)

                    header_data = header_entry[header_id]

                    if origin == "header":
                        header_data["header"].append({
                            "field": field,
                            "old_value": old_value,
                            "new_value": new_value
                        })
                    elif origin == "lines":
                        if record_id not in header_data["lines"]:
                            header_data["lines"][record_id] = {"fields": [], "rates": []}
                        header_data["lines"][record_id]["fields"].append({
                            "field": field,
                            "old_value": old_value,
                            "new_value": new_value
                        })
                    elif origin == "rate":
                        if record_id not in header_data["lines"]:
                            header_data["lines"][record_id] = {"fields": [], "rates": []}
                        header_data["lines"][record_id]["rates"].append({
                            "rate_id": record_id,
                            "field": field,
                            "old_value": old_value,
                            "new_value": new_value
                        })
        return relevant_changes

