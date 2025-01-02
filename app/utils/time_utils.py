from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Union

from app.responses import SystemResponse, InternalResponse
from app.schemas.schemas import ResponseStatus
import inspect

from app.config import settings

import pytz
import pdb
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil.relativedelta import relativedelta
from timezonefinder import TimezoneFinder


def is_start_before_end(
    start: datetime, 
    end: datetime) -> InternalResponse:
    """
    Checks if a starting date is before an ending date

    Args:
        start (datetime): Staring date
        end (datetime): Ending date

    Returns:
        InternalResponse: Internal response
    """
    status = ResponseStatus.ERROR
    origin = inspect.stack()[0].function
    
    if start < end:
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, True)
    return SystemResponse.internal_response(status, origin, "Ending date must be after starting")

def is_date_expired(date: datetime) -> InternalResponse:
    """
    Checks if a given date has passed the current time

    Args:
        date (datetime): Date to validate

    Returns:
        InternalResponse: Internal response
    """
    origin = inspect.stack()[0].function
    
    if date < datetime.now(timezone.utc):
        return SystemResponse.internal_response(ResponseStatus.ERROR, origin, False)
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, "Expired date") #Exp


def convert_to_utc(
    datetime_obj: datetime
    ) -> InternalResponse:
    """
    Convert a date object to UTC

    Args:
        datetime_obj (datetime): Date time aware (Includes TZ)

    Returns:
        InternalResponse: Internal response
    """
    
    origin = inspect.stack()[0].function
    if datetime_obj.tzinfo is None:
        return SystemResponse.internal_response(ResponseStatus.ERROR, origin, "Naive time. No TZ information provided")
    datetime_obj = datetime_obj.astimezone(ZoneInfo('UTC'))
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, datetime_obj)

def convert_naive_to_utc(
    datetime_obj: datetime, 
    timezone_str: str) -> InternalResponse:
    """
    Convert a naive date to UTC

    Args:
        datetime_obj (datetime): Naive date. Without TZ info
        timezone_str (str): Valid TZ string

    Returns:
        InternalResponse: Internal response
    """
    
    origin = inspect.stack()[0].function
    
    try:
        ZoneInfo(timezone_str)
    except ZoneInfoNotFoundError as exc:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            f"Raised ZoneInfo error: {exc}")
    
    if datetime_obj.tzinfo is None:
        datetime_obj = datetime_obj.astimezone(ZoneInfo(timezone_str))
        result = convert_to_utc(datetime_obj)
        if result.status == ResponseStatus.ERROR:
            return result
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, datetime_obj)
    return SystemResponse.internal_response(ResponseStatus.ERROR, origin, "Time aware. TZ information provided")

def repeat_daily(
    start: datetime, 
    end: datetime, 
    occurrences: int = 1) -> InternalResponse:
    """
    Repeat provided dates daily

    Args:
        start (datetime): Staring date (UTC)
        end (datetime): Ending date (UTC)
        occurrences (int, optional): Number of occurrences. Defaults to 1.

    Returns:
        InternalResponse: Internal response
    """
    repeats_dict = {}
    repeats = []
    origin = inspect.stack()[0].function
    
    result = is_start_before_end(start, end)
    if result.status == ResponseStatus.ERROR:
            return result
        
    for _ in range(occurrences):
        repeats.append((start, end))
        start += timedelta(days=1)
        end += timedelta(days=1)
    repeats_dict[0] = repeats
    
    return SystemResponse.internal_response(
        ResponseStatus.SUCCESS, 
        origin, 
        repeats_dict)

def repeat_weekly(
    start: Union[datetime, List[datetime]],
    end: Union[datetime, List[datetime]],
    occurrences: int = 1,
) -> InternalResponse:
    """
    Repeat weekly a given start and ending dates

    Args:
        start (Union[datetime, List[datetime]]): Starting dates (UTC)
        end (Union[datetime, List[datetime]]): Ending dates (UTC)
        occurrences (int, optional): Number of occurrences. Defaults to 1.

    Returns:
        InternalResponse: Internal response
    """
    repeats = []
    repeats_dict = {}
    origin = inspect.stack()[0].function
    status = ResponseStatus.SUCCESS

    if isinstance(start, datetime) and isinstance(start, datetime):
        result = is_start_before_end(start, end)
        if result.status == ResponseStatus.ERROR:
                return result
        for _ in range(occurrences):
            repeats.append((start, end))
            start += timedelta(weeks=1)
            end += timedelta(weeks=1)
        repeats_dict[0] = repeats
        return SystemResponse.internal_response(
        status, 
        origin, 
        repeats_dict)

    if isinstance(start, List) and isinstance(end, List):
        index = 0
        for item_start, item_end in zip(start, end):
            result = is_start_before_end(item_start, item_end)
            if result.status == ResponseStatus.ERROR:
                return result
            repeats_dict[str(index)] = repeats
            for _ in range(occurrences):
                repeats.append((item_start, item_end))
                item_start += timedelta(weeks=1)
                item_end += timedelta(weeks=1)
            index += 1
            repeats = []
        return SystemResponse.internal_response(
        status, 
        origin, 
        repeats_dict)
    else:
        return SystemResponse.internal_response(
        ResponseStatus.ERROR, 
        origin, 
        "Invalid dates structure provided")


def repeat_monthly(
    start: Union[datetime, List[datetime]],
    end: Union[datetime, List[datetime]],
    occurrences: int = 1) -> InternalResponse:
    """
    Repeat monthly a given start and ending dates

    Args:
        start (Union[datetime, List[datetime]]): Starting dates (UTC)
        end (Union[datetime, List[datetime]]): Ending dates (UTC)
        occurrences (int, optional): Number of occurrences. Defaults to 1.

    Returns:
        InternalResponse: Internal response
    """
    repeats = []
    repeats_dict = {}
    origin = inspect.stack()[0].function
    status = ResponseStatus.SUCCESS

    if isinstance(start, datetime) and isinstance(start, datetime):
        result = is_start_before_end(start, end)
        if result.status == ResponseStatus.ERROR:
                return result
        for _ in range(occurrences):
            repeats.append((start, end))
            start += relativedelta(months=1)
            end += relativedelta(months=1)
        repeats_dict[0] = repeats
        return SystemResponse.internal_response(
        status, 
        origin, 
        repeats_dict)

    if isinstance(start, List) and isinstance(end, List):
        index = 0
        for item_start, item_end in zip(start, end):
            result = is_start_before_end(item_start, item_end)
            if result.status == ResponseStatus.ERROR:
                return result
            repeats_dict[str(index)] = repeats
            for _ in range(occurrences):
                repeats.append((item_start, item_end))
                item_start += relativedelta(months=1)
                item_end += relativedelta(months=1)
            index += 1
            repeats = []
        return SystemResponse.internal_response(
        status, 
        origin, 
        repeats_dict)
    else:
        return SystemResponse.internal_response(
        ResponseStatus.ERROR, 
        origin, 
        "Invalid dates structure provided")

def repeat_yearly(
    start: Union[datetime, List[datetime]],
    end: Union[datetime, List[datetime]],
    occurrences: int = 1) -> InternalResponse:
    """
    Repeat yearly a given start and ending dates

    Args:
        start (Union[datetime, List[datetime]]): Starting dates (UTC)
        end (Union[datetime, List[datetime]]): Ending dates (UTC)
        occurrences (int, optional): Number of occurrences. Defaults to 1.

    Returns:
        InternalResponse: Internal response
    """
    repeats = []
    repeats_dict = {}
    origin = inspect.stack()[0].function
    status = ResponseStatus.SUCCESS

    if isinstance(start, datetime) and isinstance(start, datetime):
        result = is_start_before_end(start, end)
        if result.status == ResponseStatus.ERROR:
                return result
        for _ in range(occurrences):
            repeats.append((start, end))
            start += relativedelta(years=1)
            end += relativedelta(years=1)
        repeats_dict[0] = repeats
        return SystemResponse.internal_response(
        status, 
        origin, 
        repeats_dict)

    if isinstance(start, List) and isinstance(end, List):
        index = 0
        for item_start, item_end in zip(start, end):
            result = is_start_before_end(item_start, item_end)
            if result.status == ResponseStatus.ERROR:
                return result
            repeats_dict[str(index)] = repeats
            for _ in range(occurrences):
                repeats.append((item_start, item_end))
                item_start += relativedelta(years=1)
                item_end += relativedelta(years=1)
            index += 1
            repeats = []
        return SystemResponse.internal_response(
        status, 
        origin, 
        repeats_dict)
    else:
        return SystemResponse.internal_response(
        ResponseStatus.ERROR, 
        origin, 
        "Invalid dates structure provided")

def repeat_weekday(
    start: datetime, 
    end: datetime, 
    occurrences: int = 1) -> InternalResponse:
    """
    Repeat provided dates for weekdays

    Args:
        start (datetime): Staring date (UTC)
        end (datetime): Ending date (UTC)
        occurrences (int, optional): Number of occurrences. Defaults to 1.

    Returns:
        InternalResponse: Internal response
    """
    repeats = []
    repeats_dict = {}
    origin = inspect.stack()[0].function
    
    result = is_start_before_end(start, end)
    if result.status == ResponseStatus.ERROR:
            return result
    while occurrences > 0:
        if start.weekday() < 5:
            repeats.append((start, end))
            occurrences -= 1
        start += timedelta(days=1)
        end += timedelta(days=1)
    repeats_dict[0] = repeats
    return SystemResponse.internal_response(
        ResponseStatus.SUCCESS, 
        origin, 
        repeats_dict)

def repeat_weekend(
    start, 
    end, 
    occurrences) -> InternalResponse:
    """
    Repeat provided dates for weekends

    Args:
        start (datetime): Staring date (UTC)
        end (datetime): Ending date (UTC)
        occurrences (int, optional): Number of occurrences. Defaults to 1.

    Returns:
        InternalResponse: Internal response
    """
    repeats = []
    repeats_dict = {}
    origin = inspect.stack()[0].function
    
    result = is_start_before_end(start, end)
    if result.status == ResponseStatus.ERROR:
            return result
    while occurrences > 0:
        if start.weekday() >= 5:
            repeats.append((start, end))
            occurrences -= 1
        start += timedelta(days=1)
        end += timedelta(days=1)
    repeats_dict[0] = repeats
    return SystemResponse.internal_response(
        ResponseStatus.SUCCESS, 
        origin, 
        repeats_dict)

def set_weekdays(
    start: datetime, 
    end: datetime, 
    target_days: List[int]) -> InternalResponse:
    """
    Generate ranges of datetimes (start, end) aligned to specified target weekdays.

    Args:
        start (datetime): The starting datetime of the range.
        end (datetime): The ending datetime of the range.
        target_days (List[int]): Weekdays to align to (0=Monday, 6=Sunday).

    Returns:
        InternalResponse: Internal response
    """
    origin = inspect.stack()[0].function
    status = ResponseStatus.ERROR
    
    result = is_start_before_end(start, end)
    if result.status == ResponseStatus.ERROR:
            return result
    if not target_days:
        return SystemResponse.internal_response(
        status, 
        origin, 
        "Must provide target days")

    target_days = sorted(set(target_days))
    result, result_dict, index = [], {}, 1

    result.append((start, end))
    result_dict[0], result = result, []

    for target_day in target_days:
        days_until_target = (target_day - start.weekday() + 7) % 7
        target_date = start + timedelta(days=days_until_target)

        aligned_start = datetime.combine(target_date.date(), start.time())
        aligned_end = datetime.combine(target_date.date(), end.time())

        result.append((aligned_start, aligned_end))

        result_dict[index] = result
        result = []
        index += 1
        
    return SystemResponse.internal_response(
        ResponseStatus.SUCCESS, 
        origin, 
        result_dict)

def is_valid_date(
    date_string: str,
    format: str = "%Y-%m-%d %H:%M:%S.%f"
) -> InternalResponse:
    """
    Check if a given string is a date

    Args:
        date_string (str): Date string
        format (_type_, optional): Expected format. Defaults to "%Y-%m-%d %H:%M:%S.%f".

    Returns:
        InternalResponse: Internal response
    """
    origin = inspect.stack()[0].function
    status = ResponseStatus.ERROR

    if format is None:  # Handle cases where format is not provided
        return SystemResponse.internal_response(
            status, 
            origin, 
            f"Invalid format: {format}"
        )
    try:
        datetime.strptime(date_string, format)
        return SystemResponse.internal_response(
            ResponseStatus.SUCCESS,
            origin,
            True
        )
    except ValueError as exc:
        return SystemResponse.internal_response(
            status,
            origin,
            f"Value error: {exc}"
        )

def compute_expiration_time() -> InternalResponse:
    """
    Compute expiration time

    Returns:
        InternalResponse: Internal response
    """
    origin = inspect.stack()[0].function
    status = ResponseStatus.SUCCESS
    exp_date = datetime.now(
        timezone.utc).replace(
        tzinfo=pytz.utc) + timedelta(
        minutes=settings.email_code_expire_minutes)
        
    return SystemResponse.internal_response(
            status,
            origin,
            exp_date
            )
