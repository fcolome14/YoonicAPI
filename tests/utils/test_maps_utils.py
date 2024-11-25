import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException
import httpx
from app.utils import maps_utils as maps
from app.config import settings
from pytest_mock import MockerFixture

TEST_USER_AGENT = settings.user_agent
TEST_NOMINATIM_BASE_URL = settings.nominatim_base_url

class TestMapsUtils:
    
    @pytest.mark.asyncio
    async def test_fetch_geocode_data_success(self, mocker: MockerFixture):
        
        expected_output = [{"lat": "52.5200", "lon": "13.4050"}]
        mock_get = AsyncMock(return_value=httpx.Response(
            status_code=200,
            json=expected_output
        ))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        address = "Test address"
        result = await maps.fetch_geocode_data(address)

        assert result == expected_output
        mock_get.assert_called_once_with(f"{TEST_NOMINATIM_BASE_URL}/search",
            params={
                "q": address,
                "format": "json",
                "addressdetails": 1,
                }
            )

    @pytest.mark.asyncio
    async def test_fetch_geocode_data_error(self, mocker: MockerFixture):
 
        mock_get = AsyncMock(return_value=httpx.Response(status_code=500))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        address = "Invalid Address"
        with pytest.raises(HTTPException) as exc_info:
            await maps.fetch_geocode_data(address)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Error fetching geocode data"
        mock_get.assert_called_once_with(
            f"{TEST_NOMINATIM_BASE_URL}/search",
            params={
                "q": address,
                "format": "json",
                "addressdetails": 1,
            }
        )
