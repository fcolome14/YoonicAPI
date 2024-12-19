from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from pytest_mock import MockerFixture

from app.config import settings
from app.utils import maps_utils as maps

TEST_USER_AGENT = settings.user_agent
TEST_NOMINATIM_BASE_URL = settings.nominatim_base_url
mock_output = [{"lat": "52.345436", "lon": "12.83746", "display_name": "address_test"}]


class TestMapsUtils:

    @pytest.mark.asyncio
    async def test_fetch_geocode_data_success(self, mocker: MockerFixture):

        expected_output = {
            "status": "success",
            "point": (
                float(mock_output[0].get("lat")),
                float(mock_output[0].get("lon")),
            ),
            "address": mock_output[0].get("display_name"),
        }
        mock_get = AsyncMock(
            return_value=httpx.Response(status_code=200, json=mock_output)
        )
        mocker.patch("httpx.AsyncClient.get", mock_get)

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
    async def test_fetch_geocode_data_error(self, mocker: MockerFixture):

        expected_error = {
            "status": "error",
            "details": "Error while fetching geocode data",
        }

        mock_get = AsyncMock(return_value=httpx.Response(status_code=500))
        mocker.patch("httpx.AsyncClient.get", mock_get)
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
