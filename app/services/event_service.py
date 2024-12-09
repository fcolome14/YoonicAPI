from sqlalchemy.orm import Session
from typing import List, Union
from app.models import EventsLines
from app.schemas import NewPostInput, RateDetails
from app.services.repeater_service import select_repeater, select_repeater_custom
from app.services.rate_service import RateService, pack_rates
from app.utils import utils, time_utils

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
            return _handle_custom_each_day(db, posting_data, header_id)

        if isinstance(posting_data.line, List):
            return {"status": "error", "details": "Unexpected List type for 'line'"}
        
        return _handle_custom_week_days(db, posting_data, header_id)

@staticmethod
def _handle_custom_each_day(db: Session, posting_data: NewPostInput, header_id: int):
    """
    Handles custom mode for events occurring on each day with repetitions.
    """
    if not isinstance(posting_data.line, List):
        return {"status": "error", "details": "Line data must be a list in custom_each_day mode"}

    if posting_data.repeat:
        repeats_dict, payload = _prepare_repeats_and_payload(posting_data)
        if isinstance(repeats_dict, dict) and repeats_dict.get("status") == "error":
            return {"status": "error", "details": repeats_dict.get("details")}
        
        lines = _create_event_lines(header_id, repeats_dict, payload)
        return _finalize_lines(db, posting_data, lines)
    
    days_dict, payload = _prepare_lines_and_payload(posting_data)
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
    return _finalize_lines(db, posting_data, lines)

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
        return _finalize_lines(db, posting_data, lines)
    
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
    return _finalize_lines(db, posting_data, lines)

@staticmethod
def _create_event_lines(header_id: int, repeats: dict, payload: dict):
    """
    Creates event lines based on repeat intervals and payload.
    """
    lines = [
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
    return lines

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
    return {"status": "success", "details": f"Event created"}

@staticmethod
def _prepare_repeats_and_payload(posting_data: NewPostInput):
    """
    Prepares repeat intervals and payload for event lines.
    """
    start, end, payload_dict = [], [], {}
    for item in posting_data.line:
        start.append(item.start)
        end.append(item.end)
    
    repeats = select_repeater_custom(
        every=posting_data.when_to,
        start=start,
        end=end,
        occurrences=posting_data.occurrences
    )
    
    if isinstance(select_repeater_custom, dict) and select_repeater_custom.get("status") == "error":
            return {"status": "error", "details": select_repeater_custom.get("details")}
        
    index = 0
    for day in posting_data.line:
        payload_dict[index] = (day.capacity, day.isPublic)
        index += 1
    
    return repeats, payload_dict

@staticmethod
def _prepare_lines_and_payload(posting_data: NewPostInput):
    """
    Prepares repeat intervals and payload for event lines.
    """
    repeats, payload_dict = {}, {}
    index = 0
    for day in posting_data.line:
        payload_dict[index] = (day.capacity, day.isPublic)
        repeats[index] = (day.start, day.end)
        index += 1
    
    return repeats, payload_dict


