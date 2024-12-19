from unittest.mock import AsyncMock

import httpx
import pytest
import json

from pytest_mock import MockerFixture

from app.config import settings
from app.utils import maps_utils as maps

TEST_USER_AGENT = settings.user_agent
TEST_NOMINATIM_BASE_URL = settings.nominatim_base_url

class MockAPISession:
    
    def __init__(self, mocker: MockerFixture):
        self.mocker = mocker
    
    def mock_async_client(self, mock_output, status_code=200):
        mock_get = AsyncMock(
            return_value=httpx.Response(status_code=status_code, content=json.dumps(mock_output))
        )
        return self.mocker.patch("httpx.AsyncClient.get", mock_get)

@pytest.fixture
def mock_output():
    return [
        {
            "lat": "52.345436", 
            "lon": "12.83746", 
            "display_name": "address_test"
        }
    ]

@pytest.fixture
def expected_output(mock_output):
    return {
        "status": "success",
        "point": (
            float(mock_output[0].get("lat")),
            float(mock_output[0].get("lon")),
        ),
        "address": mock_output[0].get("display_name"),
    }
        
class TestMapsUtils:
    
    @pytest.fixture
    def mock_client(self, mocker: MockerFixture):
        return MockAPISession(mocker)

    @pytest.mark.asyncio
    async def test_fetch_geocode_data_success(self, mock_client, mock_output, expected_output):

        mock_get = mock_client.mock_async_client(mock_output)

        address = "Test address"
        result = await maps.fetch_geocode_data(address)

        assert result == expected_output
        mock_get.assert_called_once_with(
            f"{TEST_NOMINATIM_BASE_URL}/search",
            params={
                "q": address,
                "format": "json",
                "addressdetails": 1,
            },
        )

    @pytest.mark.asyncio
    async def test_fetch_geocode_data_error(self, mock_client):

        expected_error = {
            "status": "error",
            "details": "Error while fetching geocode data",
        }

        mock_get = mock_client.mock_async_client(expected_error, status_code=500)
        address = "Invalid Address"

        result = await maps.fetch_geocode_data(address)
        assert result == expected_error

        mock_get.assert_called_once_with(
            f"{TEST_NOMINATIM_BASE_URL}/search",
            params={
                "q": address,
                "format": "json",
                "addressdetails": 1,
            },
        )
