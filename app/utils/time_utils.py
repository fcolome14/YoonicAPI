from datetime import datetime, timezone, timedelta
from timezonefinder import TimezoneFinder
import pytz
from dateutil.relativedelta import relativedelta
from typing import List, Union, Tuple

def is_start_before_end(start: datetime, end: datetime) -> bool:
    """Checks if a string date is before an ending date

    Args:
        start (datetime): Staring date
        end (datetime): Ending date

    Returns:
        bool: Logic result
    """
    return start < end

def is_date_expired(date: datetime) -> bool:
    """Checks if a given date is expired

    Args:
        date (datetime): Date to be checked

    Returns:
        bool: Logic result
    """
    return date > datetime.now(timezone.utc)

def convert_to_utc(datetime_obj: datetime, timezone: str = "America/New_York") -> datetime:
    if datetime_obj.tzinfo is None:
        local_tz = pytz.timezone(timezone)
        datetime_obj = local_tz.localize(datetime_obj)
    return datetime_obj.astimezone(pytz.utc)

def get_timezone_by_coordinates(lat: float, lon: float) -> str:
    tz_finder = TimezoneFinder()

    timezone_str = tz_finder.timezone_at(lng=lon, lat=lat)
    if timezone_str is None:
        return "Timezone not found"
    return timezone_str

def convert_to_timezone(datetime_obj: datetime, timezone_str: str) -> datetime:
    timezone = pytz.timezone(timezone_str)
    return datetime_obj.astimezone(timezone)

def repeat_daily(start: datetime, end: datetime, occurrences: int = 1) -> dict:
    repeats_dict = {}
    repeats = []
    for _ in range(occurrences):
        repeats.append((start, end))
        start += timedelta(days=1)
        end += timedelta(days=1)
    repeats_dict[0] = repeats
    return repeats_dict

def repeat_weekly(start: Union[datetime, List[datetime]], end: Union[datetime, List[datetime]], occurrences: int = 1) -> dict:
    repeats = []
    repeats_dict = {}
    
    if isinstance(start, datetime) and isinstance(start, datetime):
        for _ in range(occurrences):
            repeats.append((start, end))
            start += timedelta(weeks=1)
            end += timedelta(weeks=1)
        repeats_dict[0] = repeats
        return repeats_dict
    
    if isinstance(start, List) and isinstance(end, List):
        index = 0
        for item_start, item_end in zip(start, end):
            repeats_dict[str(index)] = repeats
            for _ in range(occurrences):
                repeats.append((item_start, item_end))
                item_start += timedelta(weeks=1)
                item_end += timedelta(weeks=1)
            index += 1
            repeats = []
        return repeats_dict
    
    else:
        return {"status": "error"}

def repeat_monthly(start: Union[datetime, List[datetime]], end: Union[datetime, List[datetime]], occurrences: int = 1) -> dict:
    repeats = []
    repeats_dict = {}
    
    if isinstance(start, datetime) and isinstance(start, datetime):
        for _ in range(occurrences):
            repeats.append((start, end))
            start += relativedelta(months=1)
            end += relativedelta(months=1)
        repeats_dict[0] = repeats
        return repeats_dict
    
    if isinstance(start, List) and isinstance(end, List):
        index = 0
        for item_start, item_end in zip(start, end):
            repeats_dict[str(index)] = repeats
            for _ in range(occurrences):
                repeats.append((item_start, item_end))
                item_start += relativedelta(months=1)
                item_end += relativedelta(months=1)
            index += 1
            repeats = []
        return repeats_dict
    
    else:
        return {"status": "error"}

def repeat_yearly(start: Union[datetime, List[datetime]], end: Union[datetime, List[datetime]], occurrences: int = 1) -> dict:
    repeats = []
    repeats_dict = {}
    
    if isinstance(start, datetime) and isinstance(start, datetime):
        for _ in range(occurrences):
            repeats.append((start, end))
            start += relativedelta(years=1)
            end += relativedelta(years=1)
        repeats_dict[0] = repeats
        return repeats_dict
    
    if isinstance(start, List) and isinstance(end, List):
        index = 0
        for item_start, item_end in zip(start, end):
            repeats_dict[str(index)] = repeats
            for _ in range(occurrences):
                repeats.append((item_start, item_end))
                item_start += relativedelta(years=1)
                item_end += relativedelta(years=1)
            index += 1
            repeats = []
        return repeats_dict
    
    else:
        return {"status": "error"}

def repeat_weekday(start: datetime, end: datetime, occurrences: int = 1) -> dict:
    repeats = []
    repeats_dict = {}
    
    while occurrences > 0:
        if start.weekday() < 5:
            repeats.append((start, end))
            occurrences -= 1
        start += timedelta(days=1)
        end += timedelta(days=1)
    repeats_dict[0] = repeats
    return repeats_dict

def repeat_weekend(start, end, occurrences) -> dict:
    repeats = []
    repeats_dict = {}
    
    while occurrences > 0:
        if start.weekday() >= 5:
            repeats.append((start, end))
            occurrences -= 1
        start += timedelta(days=1)
        end += timedelta(days=1)
    repeats_dict[0] = repeats
    return repeats_dict

def set_week_days(start: datetime, end: datetime, target_days: List[int]) -> List[Tuple[datetime, datetime]]:
    """
    Generate ranges of datetimes (start, end) aligned to specified target weekdays.

    Args:
        start (datetime): The starting datetime of the range.
        end (datetime): The ending datetime of the range.
        target_days (List[int]): Weekdays to align to (0=Monday, 6=Sunday).

    Returns:
        List[Tuple[datetime, datetime]]: List of (start, end) ranges for the target weekdays.
    """
    if not target_days:
        raise ValueError("target_days cannot be empty")
    if start > end:
        raise ValueError("Start datetime must be before end datetime")

    target_days = sorted(set(target_days))
    result = []
    result_dict = {}
    index = 1
    
    result.append((start, end))
    result_dict[0] = result
    result = []

    for target_day in target_days:
        days_until_target = (target_day - start.weekday() + 7) % 7
        target_date = start + timedelta(days=days_until_target)

        aligned_start = datetime.combine(target_date.date(), start.time())
        aligned_end = datetime.combine(target_date.date(), end.time())

        result.append((aligned_start, aligned_end))
        
        result_dict[index] = result
        result = []
        index += 1
        
    return result_dict
         

