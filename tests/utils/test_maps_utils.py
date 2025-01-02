from unittest.mock import AsyncMock

import httpx
import pytest
import json

from app.responses import SystemResponse, InternalResponse
from app.schemas.schemas import ResponseStatus
import inspect
from datetime import datetime

import pdb
import copy
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
def expected_output():
    return InternalResponse(
        status=ResponseStatus.SUCCESS,
        origin="",
        message="",
        timestamp=datetime.now().isoformat(),
    )
        
class TestMapsUtils:
    
    @pytest.fixture
    def mock_client(self, mocker: MockerFixture):
        return MockAPISession(mocker)
    
    @pytest.fixture
    def mock_input(self):
        return (52.345436, 12.83746)
    
    @pytest.fixture
    def mock_bound_box_input(self, mock_input):
        return mock_input, 10, 0
    
    @pytest.fixture
    def mock_OSM_API_single_result(self, mock_input):
        return {
                "lat": mock_input[0], 
                "lon": mock_input[1], 
                "display_name": "address_test",
                "error": None
            }
    
    @pytest.fixture
    def mock_bound_box_output(self):
        return {
            'min_lat': 52.25550383940813, 
            'max_lat': 52.43536816059187, 
            'min_lon': 12.690247181675124, 
            'max_lon': 12.984672818324876
            }
    
    @pytest.fixture
    def mock_OSM_API_multiple_result(self, mock_OSM_API_single_result):
        return [copy.deepcopy(mock_OSM_API_single_result) for _ in range(3)]
        
    @pytest.fixture
    def mock_geocode_result(
        self, 
        mock_OSM_API_single_result, mock_input):
        return mock_input[0], mock_input[1],{
            'point': (mock_input[0], mock_input[1]), 
            'address': mock_OSM_API_single_result["display_name"]}

    @pytest.mark.asyncio
    async def test_fetch_geocode_data_succeed(
        self, 
        mock_client, 
        mock_OSM_API_single_result, 
        mock_geocode_result,
        expected_output: InternalResponse) -> InternalResponse:
        
        mock_OSM_API_single_result_list = []
        address = "Test address"
        mock_OSM_API_single_result_list.append(mock_OSM_API_single_result)
        
        _, _, geocode_output = mock_geocode_result
        mock_client.mock_async_client(mock_OSM_API_single_result_list)
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.origin = "fetch_geocode_data"
        expected_output.message = geocode_output

        result: InternalResponse = await maps.fetch_geocode_data(address)
        expected_output.timestamp = result.timestamp

        assert result == expected_output
        
    @pytest.mark.parametrize("errorAPI, message", [
    (True, "Site not found")
    ])
    @pytest.mark.asyncio
    async def test_fetch_geocode_data_error(
        mock_client,
        errorAPI,
        message,
        mock_geocode_result,
        expected_output: InternalResponse
    ):
        
        address = "Test address"
        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "fetch_geocode_data"
        expected_output.message = message
        
        mock_client.get = AsyncMock(return_value=AsyncMock(
            status_code=200 if not errorAPI else 404,
            json=AsyncMock(return_value=mock_geocode_result),
        ))

        result: InternalResponse = await maps.fetch_geocode_data(address)
        expected_output.timestamp = result.timestamp

        assert result == expected_output
    
    @pytest.mark.asyncio
    async def test_fetch_reverse_geocode_data_succeed(
        self, 
        mock_client, 
        mock_OSM_API_single_result, 
        mock_geocode_result,
        expected_output: InternalResponse) -> InternalResponse:
        
        lat, lon, geocode_output = mock_geocode_result
        mock_client.mock_async_client(mock_OSM_API_single_result)
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.origin = "fetch_reverse_geocode_data"
        expected_output.message = geocode_output

        result: InternalResponse = await maps.fetch_reverse_geocode_data(
            lat, lon)
        expected_output.timestamp = result.timestamp

        assert result == expected_output
        
    @pytest.mark.parametrize("errorAPI, message", [
    (True, "Site not found")
    ])
    @pytest.mark.asyncio
    async def test_fetch_reverse_geocode_data_errors(
        self,
        mock_client,
        mock_input,
        errorAPI,
        message,
        expected_output: InternalResponse
    ):
        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "fetch_reverse_geocode_data"
        expected_output.message = message
        
        if errorAPI:
            mock_client.mock_async_client({})

        result: InternalResponse = await maps.fetch_reverse_geocode_data(
            mock_input[0], mock_input[1])
        expected_output.timestamp = result.timestamp

        assert result == expected_output
    
    def test_get_bounding_area_succeed(
        self,
        mock_bound_box_input,
        mock_bound_box_output,
        expected_output: InternalResponse):
        
        mock_position, radius, units = mock_bound_box_input
        input = [mock_position[0], mock_position[1]]
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.origin = "get_bounding_area"
        expected_output.message = mock_bound_box_output
        
        result = maps.get_bounding_area(input, radius, units)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize("mock_inputErrors", [
    ((52.345436, 12.83746), 10.1, 0),
    ((12.83746), 10, 0),
    ((52, 12), 10, 0),
    ((52.345436, 12.83746), 10, 0.5),
    ("test", 10, 0),
    ((52.345436, 12.83746), "test", 0),
    ((52.345436, 12.83746), 10, "test"),
    ((52.345436, 12.83746), 10, 34),
    ])
    def test_get_bounding_area_errors(
        self,
        mock_inputErrors,
        expected_output: InternalResponse):
        
        mock_position, radius, units = mock_inputErrors
        input = mock_position
        if isinstance(input, list):
            input = [mock_position[0], mock_position[1]]
        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "get_bounding_area"
        expected_output.message = "Invalid input types"
        
        result = maps.get_bounding_area(input, radius, units)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output