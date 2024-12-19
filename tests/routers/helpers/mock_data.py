from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import List, Union

from app.schemas import bases, schemas


def create_mock_rate(single=True):
    """
    Create a mock rate. If `single` is False, return a list of rates.
    """
    rate = bases.RateDetails(title="Rate Test", amount=33.5, currency="EUR")
    return rate if not single else [rate, deepcopy(rate)]


def create_mock_line(rate, custom_each_day: bool):
    """
    Create a mock line. If `custom_each_day` is False, return a list of lines.
    """
    line = schemas.EventLines(
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc) + timedelta(hours=10),
        rate=rate,
        isPublic=True,
        capacity=10,
    )
    return line if not custom_each_day else [line, deepcopy(line)]


def create_mock_input(
    line: Union[List[schemas.EventLines], schemas.EventLines],
    custom_each_day: bool,
    custom_option_selected: bool,
    repeat: bool,
    where_to: int = 0,
):
    """
    Create a mock input using the provided line (single or list).
    """
    return schemas.NewPostInput(
        repeat=repeat,
        occurrences=2,
        when_to=where_to,
        custom_option_selected=custom_option_selected,
        for_days=[0, 1, 3],
        custom_each_day=custom_each_day,
        title="Test",
        description=None,
        location="C/Test, 123",
        user_timezone="tz",
        category=2,
        line=line,
        owner_id=1,
    )


def update_mock_input(mock_input, **updates):
    """
    Dynamically update fields in the mock input.
    """
    updated_input = deepcopy(mock_input)
    for key, value in updates.items():
        setattr(updated_input, key, value)
    return updated_input
