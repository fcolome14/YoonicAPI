from datetime import datetime
from typing import List, Union

from app.utils import time_utils


def select_repeater(
    every: int, start: datetime, end: datetime, occurrences: int = 1
) -> Union[List[datetime], dict]:
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
        return {"status": "error", "details": "Invalid 'every' value"}


def select_repeater_custom(
    every: int, start: datetime, end: datetime, occurrences: int = 1
) -> Union[List[datetime], dict]:
    if every == 0:  # Weekly
        return time_utils.repeat_weekly(start, end, occurrences)
    elif every == 1:  # Monthly
        return time_utils.repeat_monthly(start, end, occurrences)
    elif every == 2:  # Yearly
        return time_utils.repeat_yearly(start, end, occurrences)
    else:
        return {"status": "error", "details": "Invalid 'every' value"}
