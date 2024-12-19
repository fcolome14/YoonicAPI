from datetime import datetime, timedelta, timezone

import pytest

from app.utils import time_utils


@pytest.mark.parametrize(
    "mocked_date, expected_result",
    [
        (datetime.now(timezone.utc) + timedelta(hours=2), True),
        (datetime.now(timezone.utc) - timedelta(hours=2), False),
        (datetime.now(timezone.utc), False),
    ],
)
class TestTimeUtils:
    """Time utils testing"""

    def test_is_start_before_end(self, mocked_date, expected_result):
        """Test a starting date is before an ending date"""
        start_date = datetime.now(timezone.utc)
        response = time_utils.is_start_before_end(start=start_date, end=mocked_date)

        assert response == expected_result

    def test_is_date_expired(self, mocked_date, expected_result):
        """Test if a given date has expired"""
        response = time_utils.is_date_expired(date=mocked_date)

        assert response == expected_result
