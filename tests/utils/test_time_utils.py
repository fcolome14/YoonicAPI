from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.responses import SystemResponse
from app.schemas.schemas import ResponseStatus, InternalResponse
from app.config import settings

import pdb
import pytz
import copy

import pytest
from pytest_mock import MockerFixture
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.utils import time_utils

#TODO: REFACTOR

@pytest.fixture
def expected_output():
    return InternalResponse(
        status=ResponseStatus.SUCCESS,
        origin="",
        message="",
        timestamp=datetime.now().isoformat(),
    )

@pytest.fixture
def schedule_single_repetition_input():
    start  = datetime(2024, 12, 22, 15, 30)
    end = start + timedelta(hours=1)
    occurrences = 3
    return start, end, occurrences

@pytest.fixture
def target_days_mapping(schedule_single_repetition_input):
    start, end, _ = schedule_single_repetition_input
    return start, end, [0, 3, 5]

@pytest.fixture
def schedule_multiple_repetition_input():
    start  = [
        datetime(2024, 12, 22, 15, 30),
        datetime(2024, 12, 24, 15, 30),
        datetime(2024, 12, 27, 15, 30)
        ]
    end  = [
        datetime(2024, 12, 22, 16, 30),
        datetime(2024, 12, 25, 17, 00),
        datetime(2024, 12, 27, 16, 30)
        ]
    occurrences = 3
    return (start, end, occurrences)
        
class TestTimeUtils:

    def test_is_start_before_end_succeed(
        self, 
        expected_output: InternalResponse) -> InternalResponse:
        
        start = datetime.now()
        end = start + timedelta(hours=1)
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.origin = "is_start_before_end"
        expected_output.message = True
        
        result: InternalResponse = time_utils.is_start_before_end(start, end)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_is_start_before_end_errors(
        self, 
        expected_output: InternalResponse) -> InternalResponse:
        
        start = datetime.now(timezone.utc)
        end = start - timedelta(hours=1)
        
        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "is_start_before_end"
        expected_output.message = "Ending date must be after starting"
        
        result: InternalResponse = time_utils.is_start_before_end(start, end)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_is_date_expired_succeed(
        self, 
        expected_output: InternalResponse) -> InternalResponse:
        
        date = datetime.now(timezone.utc) - timedelta(hours=1)
        
        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "is_date_expired"
        expected_output.message = False
        
        result: InternalResponse = time_utils.is_date_expired(date)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_is_date_expired_errors(
        self, 
        expected_output: InternalResponse) -> InternalResponse:
        
        date = datetime.now(timezone.utc) + timedelta(hours=1)
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.origin = "is_date_expired"
        expected_output.message = "Expired date"
        
        result: InternalResponse = time_utils.is_date_expired(date)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output

    @pytest.mark.parametrize("tzAware", [
        True,
        False
    ])
    def test_convert_to_utc(
        self, 
        tzAware,
        expected_output: InternalResponse) -> InternalResponse:
        
        date = datetime(2024, 12, 22, 15, 30)
        
        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "convert_to_utc"
        expected_output.message = "Naive time. No TZ information provided"
    
        if tzAware:
            expected_output.status = ResponseStatus.SUCCESS
            date = datetime(2024, 12, 22, 15, 30, tzinfo=ZoneInfo('UTC'))
            expected_output.message = date
        
        result: InternalResponse= time_utils.convert_to_utc(date)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_convert_naive_to_utc_succeed(
        self, 
        mocker: MockerFixture,
        expected_output: InternalResponse) -> InternalResponse:
        
        date = datetime(2024, 12, 22, 15, 30)
        timezone = 'America/New_York'
        date_aware = date.astimezone(ZoneInfo('UTC'))
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_convert_to_utc_output = copy.deepcopy(expected_output)
        
        expected_convert_to_utc_output.origin = "convert_to_utc"
        expected_convert_to_utc_output.message = date_aware
        
        expected_output.origin = "convert_naive_to_utc"
        expected_output.message = date_aware
        
        mocker.patch("app.utils.time_utils.convert_to_utc", 
                     return_value=expected_convert_to_utc_output)
        
        result: InternalResponse= time_utils.convert_naive_to_utc(date, timezone)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize("tzError, tzNoneError, message", [
        (True, False, "Raised ZoneInfo error"),
        (False, True, "Time aware. TZ information provided"),
        (False, False, "Naive time. No TZ information provided"),
    ])
    def test_convert_naive_to_utc_errors(
        self, 
        mocker: MockerFixture,
        tzError, 
        tzNoneError,
        message,
        expected_output: InternalResponse) -> InternalResponse:
        
        date = datetime(2024, 12, 22, 15, 30)
        timezone = 'America/New_York'
        date_aware = date.astimezone(ZoneInfo('UTC'))
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_convert_to_utc_output = copy.deepcopy(expected_output)
        
        expected_convert_to_utc_output.origin = "convert_to_utc"
        expected_convert_to_utc_output.message = date_aware
        
        expected_output.origin = "convert_naive_to_utc"
        expected_output.message = date_aware
        
        if tzError:
            timezone = 'Invalid/TZ'
            expected_output.status = ResponseStatus.ERROR
            detailError = "No time zone found with key Invalid/TZ"
            mocker.patch("zoneinfo.ZoneInfo", side_effect=ZoneInfoNotFoundError(detailError))
            expected_output.message = f"{message}: '{detailError}'"
        if tzNoneError:
            date = date.astimezone(ZoneInfo(timezone))
            expected_output.status = ResponseStatus.ERROR
            expected_output.message = message
        if not tzError and not tzNoneError:
            expected_convert_to_utc_output.status = ResponseStatus.ERROR
            expected_output.status = ResponseStatus.ERROR
            expected_convert_to_utc_output.message = message
            expected_output.message = message
            expected_output.origin = "convert_to_utc"
            mocker.patch("app.utils.time_utils.convert_to_utc", 
                     return_value=expected_convert_to_utc_output)
            
        mocker.patch("app.utils.time_utils.convert_to_utc", 
                     return_value=expected_convert_to_utc_output)
        
        result: InternalResponse= time_utils.convert_naive_to_utc(date, timezone)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
        
    def test_repeat_daily_succeed(
        self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_single_repetition_input
        schedule_dict = {0: [
        (datetime(2024, 12, 22, 15, 30), datetime(2024, 12, 22, 16, 30)),
        (datetime(2024, 12, 23, 15, 30), datetime(2024, 12, 23, 16, 30)),
        (datetime(2024, 12, 24, 15, 30), datetime(2024, 12, 24, 16, 30))
        ]}
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = True
        
        expected_output.origin = "repeat_daily"
        expected_output.message = schedule_dict
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_daily(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_repeat_daily_errors(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_single_repetition_input
        
        expected_output.status = ResponseStatus.ERROR
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = "Ending date must be after starting"
        
        expected_output.origin = expected_start_before_end_output.origin
        expected_output.message = expected_start_before_end_output.message
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_daily(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize("singleInput", [
        True,
        False
    ])
    def test_repeat_weekly_succeed(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        singleInput,
        schedule_multiple_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_multiple_repetition_input
        schedule_dict = {
                '0': [
                    (datetime(2024, 12, 22, 15, 30), datetime(2024, 12, 22, 16, 30)),
                    (datetime(2024, 12, 29, 15, 30), datetime(2024, 12, 29, 16, 30)),
                    (datetime(2025, 1, 5, 15, 30), datetime(2025, 1, 5, 16, 30))
                ],
                '1': [
                    (datetime(2024, 12, 24, 15, 30), datetime(2024, 12, 25, 17, 0)),
                    (datetime(2024, 12, 31, 15, 30), datetime(2025, 1, 1, 17, 0)),
                    (datetime(2025, 1, 7, 15, 30), datetime(2025, 1, 8, 17, 0))
                ],
                '2': [
                    (datetime(2024, 12, 27, 15, 30), datetime(2024, 12, 27, 16, 30)),
                    (datetime(2025, 1, 3, 15, 30), datetime(2025, 1, 3, 16, 30)),
                    (datetime(2025, 1, 10, 15, 30), datetime(2025, 1, 10, 16, 30))
                ]
            }
        
        if singleInput:
            start, end, occurrences = schedule_single_repetition_input
            schedule_dict = {0: [
            (datetime(2024, 12, 22, 15, 30), datetime(2024, 12, 22, 16, 30)),
            (datetime(2024, 12, 29, 15, 30), datetime(2024, 12, 29, 16, 30)),
            (datetime(2025, 1, 5, 15, 30), datetime(2025, 1, 5, 16, 30))
            ]}
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = True
        
        expected_output.origin = "repeat_weekly"
        expected_output.message = schedule_dict
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_weekly(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize("singleInput", [
        True,
        False
    ])
    def test_repeat_weekly_errors(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        singleInput,
        schedule_multiple_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_multiple_repetition_input
        if singleInput:
            start, end, occurrences = schedule_single_repetition_input
        
        expected_output.status = ResponseStatus.ERROR
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = "Ending date must be after starting"
        
        expected_output.origin = expected_start_before_end_output.origin
        expected_output.message = expected_start_before_end_output.message
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_weekly(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize("singleInput", [
        True,
        False
    ])
    def test_repeat_monthly_succeed(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        singleInput,
        schedule_multiple_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_multiple_repetition_input
        schedule_dict = {
                '0': [
                    (datetime(2024, 12, 22, 15, 30), datetime(2024, 12, 22, 16, 30)),
                    (datetime(2025, 1, 22, 15, 30), datetime(2025, 1, 22, 16, 30)),
                    (datetime(2025, 2, 22, 15, 30), datetime(2025, 2, 22, 16, 30))
                ],
                '1': [
                    (datetime(2024, 12, 24, 15, 30), datetime(2024, 12, 25, 17, 0)),
                    (datetime(2025, 1, 24, 15, 30), datetime(2025, 1, 25, 17, 0)),
                    (datetime(2025, 2, 24, 15, 30), datetime(2025, 2, 25, 17, 0))
                ],
                '2': [
                    (datetime(2024, 12, 27, 15, 30), datetime(2024, 12, 27, 16, 30)),
                    (datetime(2025, 1, 27, 15, 30), datetime(2025, 1, 27, 16, 30)),
                    (datetime(2025, 2, 27, 15, 30), datetime(2025, 2, 27, 16, 30))
                ]
            }
        
        if singleInput:
            start, end, occurrences = schedule_single_repetition_input
            schedule_dict = {
                0: [
                    (datetime(2024, 12, 22, 15, 30), datetime(2024, 12, 22, 16, 30)),
                    (datetime(2025, 1, 22, 15, 30), datetime(2025, 1, 22, 16, 30)),
                    (datetime(2025, 2, 22, 15, 30), datetime(2025, 2, 22, 16, 30))
                    ]
                }
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = True
        
        expected_output.origin = "repeat_monthly"
        expected_output.message = schedule_dict
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_monthly(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize("singleInput", [
        True,
        False
    ])
    def test_repeat_monthly_errors(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        singleInput,
        schedule_multiple_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_multiple_repetition_input
        if singleInput:
            start, end, occurrences = schedule_single_repetition_input
        
        expected_output.status = ResponseStatus.ERROR
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = "Ending date must be after starting"
        
        expected_output.origin = expected_start_before_end_output.origin
        expected_output.message = expected_start_before_end_output.message
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_monthly(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize("singleInput", [
        True,
        False
    ])
    def test_repeat_yearly_succeed(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        singleInput,
        schedule_multiple_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_multiple_repetition_input
        schedule_dict = {
                '0': [
                    (datetime(2024, 12, 22, 15, 30), datetime(2024, 12, 22, 16, 30)),
                    (datetime(2025, 12, 22, 15, 30), datetime(2025, 12, 22, 16, 30)),
                    (datetime(2026, 12, 22, 15, 30), datetime(2026, 12, 22, 16, 30)),
                ],
                '1': [
                    (datetime(2024, 12, 24, 15, 30), datetime(2024, 12, 25, 17, 0)),
                    (datetime(2025, 12, 24, 15, 30), datetime(2025, 12, 25, 17, 0)),
                    (datetime(2026, 12, 24, 15, 30), datetime(2026, 12, 25, 17, 0)),
                ],
                '2': [
                    (datetime(2024, 12, 27, 15, 30), datetime(2024, 12, 27, 16, 30)),
                    (datetime(2025, 12, 27, 15, 30), datetime(2025, 12, 27, 16, 30)),
                    (datetime(2026, 12, 27, 15, 30), datetime(2026, 12, 27, 16, 30)),
                ]
            }
        
        if singleInput:
            start, end, occurrences = schedule_single_repetition_input
            schedule_dict = {
                0: [
                    (datetime(2024, 12, 22, 15, 30), datetime(2024, 12, 22, 16, 30)),
                    (datetime(2025, 12, 22, 15, 30), datetime(2025, 12, 22, 16, 30)),
                    (datetime(2026, 12, 22, 15, 30), datetime(2026, 12, 22, 16, 30))
                    ]
                }
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = True
        
        expected_output.origin = "repeat_yearly"
        expected_output.message = schedule_dict
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_yearly(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize("singleInput", [
        True,
        False
    ])
    def test_repeat_yearly_errors(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        singleInput,
        schedule_multiple_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_multiple_repetition_input
        if singleInput:
            start, end, occurrences = schedule_single_repetition_input
        
        expected_output.status = ResponseStatus.ERROR
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = "Ending date must be after starting"
        
        expected_output.origin = expected_start_before_end_output.origin
        expected_output.message = expected_start_before_end_output.message
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_yearly(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_repeat_weekday_succeed(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_single_repetition_input
        schedule_dict = {0: [
        (datetime(2024, 12, 23, 15, 30), datetime(2024, 12, 23, 16, 30)),
        (datetime(2024, 12, 24, 15, 30), datetime(2024, 12, 24, 16, 30)),
        (datetime(2024, 12, 25, 15, 30), datetime(2024, 12, 25, 16, 30))
        ]}
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = True
        
        expected_output.origin = "repeat_weekday"
        expected_output.message = schedule_dict
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_weekday(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_repeat_weekday_errors(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_single_repetition_input
        
        expected_output.status = ResponseStatus.ERROR
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = "Ending date must be after starting"
        
        expected_output.origin = expected_start_before_end_output.origin
        expected_output.message = expected_start_before_end_output.message
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_weekday(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_repeat_weekend_succeed(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_single_repetition_input
        schedule_dict = {0: [
        (datetime(2024, 12, 22, 15, 30), datetime(2024, 12, 22, 16, 30)),
        (datetime(2024, 12, 28, 15, 30), datetime(2024, 12, 28, 16, 30)),
        (datetime(2024, 12, 29, 15, 30), datetime(2024, 12, 29, 16, 30))
        ]}
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = True
        
        expected_output.origin = "repeat_weekend"
        expected_output.message = schedule_dict
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_weekend(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_repeat_weekend_errors(self, 
        mocker: MockerFixture,
        schedule_single_repetition_input,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, occurrences = schedule_single_repetition_input
        
        expected_output.status = ResponseStatus.ERROR
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = "Ending date must be after starting"
        
        expected_output.origin = expected_start_before_end_output.origin
        expected_output.message = expected_start_before_end_output.message
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.repeat_weekend(start, end, occurrences)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_set_weekdays_succeed(
        self,
        mocker: MockerFixture,
        target_days_mapping,
        expected_output: InternalResponse):
        
        start, end, target_days = target_days_mapping
        schedule_dict = ({
        0: [(datetime(2024, 12, 22, 15, 30), datetime(2024, 12, 22, 16, 30))],
        1: [(datetime(2024, 12, 23, 15, 30), datetime(2024, 12, 23, 16, 30))],
        2: [(datetime(2024, 12, 26, 15, 30), datetime(2024, 12, 26, 16, 30))],
        3: [(datetime(2024, 12, 28, 15, 30), datetime(2024, 12, 28, 16, 30))]
        })
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = True
        
        expected_output.origin = "set_weekdays"
        expected_output.message = schedule_dict
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.set_weekdays(start, end, target_days)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_set_weekdays_errors(
        self,
        mocker: MockerFixture,
        target_days_mapping,
        expected_output: InternalResponse) -> InternalResponse:
        
        start, end, target_days = target_days_mapping
        
        expected_output.status = ResponseStatus.ERROR
        expected_start_before_end_output = copy.deepcopy(expected_output)
        
        expected_start_before_end_output.origin = "is_start_before_end"
        expected_start_before_end_output.message = "Ending date must be after starting"
        
        expected_output.origin = expected_start_before_end_output.origin
        expected_output.message = expected_start_before_end_output.message
        
        mocker.patch("app.utils.time_utils.is_start_before_end", 
                     return_value=expected_start_before_end_output)
        
        result: InternalResponse = time_utils.set_weekdays(start, end, target_days)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    def test_is_valid_date_succeed(
        self,
        expected_output: InternalResponse) -> InternalResponse:
        
        date = "2024-12-18T07:00:08.633Z"
        format = "%Y-%m-%dT%H:%M:%S.%fZ"
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.origin = "is_valid_date"
        expected_output.message = True
        
        result: InternalResponse = time_utils.is_valid_date(date, format)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize("date, format, message", [
        ("2024-12-18T07:00:08.633Z", None, "Invalid format: None"),
        ("Invalid-Date", 
        "%Y-%m-%dT%H:%M:%S.%fZ", 
        "Value error: time data 'Invalid-Date' does not match format '%Y-%m-%dT%H:%M:%S.%fZ'"),
        ])
    def test_is_valid_date_errors(
        self,
        expected_output: InternalResponse,
        date, 
        format, 
        message) -> InternalResponse:

        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "is_valid_date"
        expected_output.message = message
        
        result = time_utils.is_valid_date(date, format)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
        
    def test_compute_expiration_time_succeed(
        self,
        expected_output: InternalResponse) -> InternalResponse:
        
        date = datetime.now(
        timezone.utc).replace(
        tzinfo=pytz.utc) + timedelta(
        minutes=settings.email_code_expire_minutes)
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.origin = "compute_expiration_time"
        expected_output.message = date
        
        result = time_utils.compute_expiration_time()
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output