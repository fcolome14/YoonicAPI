from datetime import datetime
from typing import List, Union

from app.utils import time_utils

from app.responses import SystemResponse, InternalResponse
from app.schemas.schemas import ResponseStatus
import inspect


def select_repeater_single_mode(
    every: int, dates: tuple[datetime], occurrences: int = 1
) -> Union[List[datetime], dict]:
    
    origin = inspect.stack()[0].function
    if isinstance(dates, list):
        start, end = dates[0]
    else:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, origin, 
            "Expected list of dates")
 
    if every == 0:  # Daily
        return time_utils.repeat_daily(start, end, occurrences)
    elif every == 1:  # Weekly
        return time_utils.repeat_weekly(start, end, occurrences)
    elif every == 2:  # Monthly
        return time_utils.repeat_monthly(start, end, occurrences)
    elif every == 3:  # Weekdays
        return time_utils.repeat_weekday(start, end, occurrences)
    elif every == 4:  # Weekends
        return time_utils.repeat_weekend(start, end, occurrences)
    else:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, origin, 
            f"Invalid 'every' value ({str(every)})")


def select_repeater_custom_mode(
    every: int, dates: tuple[datetime], occurrences: int = 1
) -> Union[List[datetime], dict]:
    
    origin = inspect.stack()[0].function
    
    result: InternalResponse = _prepare_data(dates)
    if result.status == ResponseStatus.ERROR:
        return result
    start, end = result.message
    
    if every == 0:  # Weekly
        return time_utils.repeat_weekly(start, end, occurrences)
    elif every == 1:  # Monthly
        return time_utils.repeat_monthly(start, end, occurrences)
    elif every == 2:  # Yearly
        return time_utils.repeat_yearly(start, end, occurrences)
    else:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, origin, 
            f"Invalid 'every' value ({str(every)})")

def _prepare_data(dates: tuple[datetime]):
    origin = inspect.stack()[0].function
    
    if isinstance(dates, list) and len(dates) == 1:
        return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, origin, dates[0])
    elif isinstance(dates, list) and len(dates) > 1:
        start, end = [], []
        for _start, _end in dates:
            start.append(_start)
            end.append(_end)
        return SystemResponse.internal_response(
        ResponseStatus.SUCCESS, origin, (start, end))
    elif isinstance(dates, dict) and len(dates) > 1:
        start, end = [], []
        for _, value in dates.items():
            for _start, _end in value:
                start.append(_start)
                end.append(_end)
        return SystemResponse.internal_response(
        ResponseStatus.SUCCESS, origin, (start, end))
    else:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, origin, 
            "Expected list of dates")
