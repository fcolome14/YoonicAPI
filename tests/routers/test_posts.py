import pytest
from pytest_mock import MockerFixture
from fastapi import HTTPException
from app.schemas import schemas
import app.models
from app.exception_handlers import custom_http_exception_handler
from app.routers import posts
from datetime import datetime, timezone, timedelta
import json

class TestPosts:
    
    @pytest.fixture
    def mock_request(self, mocker: MockerFixture):
        mock_request = mocker.Mock()
        
        mock_request.headers = {
            "request-id": "default_request_id",
            "client-type": "unknown"
        }
        
        return mock_request
    
    @pytest.fixture
    def mock_fetched_data(self):
        
        return schemas.NewPostInput(
            title = "Test",
            description = None,
            start = datetime.now(timezone.utc),
            end = datetime.now(timezone.utc) + timedelta(hours=10),
            location = "C/Test, 123",
            isPublic = True,
            category = 1,
            tags = None,
            cost = 0,
            currency = None,
            capacity =None,
            owner_id=1
        )
        
    
    @pytest.mark.asyncio
    async def test_create_post_succeed(self, mocker: MockerFixture, mock_request, mock_fetched_data):
        
        db_session = mocker.Mock()

        expected_output = schemas.SuccessResponse(
            status="success",
            message="New event created",
            data={},
            meta={
                "request_id": mock_request.headers.get("request-id"), 
                "client": mock_request.headers.get("client-type")
            }
        )
        
        response = await posts.create_post(posting_data=mock_fetched_data, db=db_session, request=mock_request)
        assert expected_output == response
    
    @pytest.mark.parametrize("mock_type, mock_message, mock_details, mock_geodata_response, mock_is_start_before_end", [
        ("NewPost", "Invalid datetimes", "Starting date must be before ending date", {"status": "error", "details": "Site not found"}, False),
        
        ("OSM", "Error while fetching geocode data", None, {"status": "error", "details": "Error while fetching geocode data"}, True)
    ])
    
    @pytest.mark.asyncio
    async def test_create_post_exceptions(self, mocker: MockerFixture, mock_request, mock_fetched_data, 
                                          mock_message, mock_details, mock_geodata_response, mock_is_start_before_end, mock_type):
        
        db_session = mocker.Mock()
    
        mocker.patch("app.routers.posts.time_utils.is_start_before_end", return_value=mock_is_start_before_end)
        mocker.patch("app.routers.posts.maps_utils.fetch_geocode_data", return_value=mock_geodata_response)
        mocker.patch("app.routers.posts.maps_utils.fetch_reverse_geocode_data", return_value=mock_geodata_response)
        expected_error = {
            "status": "error",
            "message": mock_message,
            "data": {
                "type": mock_type,
                "message": mock_message,
                "details": mock_details
            },
            "meta": {
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type")
            }
        }
        
        with pytest.raises(HTTPException) as exception_data:
            await posts.create_post(posting_data=mock_fetched_data, db=db_session, request=mock_request)
        
        error_output = custom_http_exception_handler(mock_request, exception_data.value)
        error_body = error_output.body.decode("utf-8")
        error_response = json.loads(error_body)
        
        assert expected_error == error_response
        