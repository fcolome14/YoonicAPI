from datetime import datetime, timezone

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