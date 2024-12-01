import pytest
from pytest_mock import MockerFixture
from fastapi import HTTPException
from app.schemas import schemas
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
    def mock_post(self, mocker: MockerFixture):
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
    async def test_create_post_succeed(self, mocker: MockerFixture, mock_request, mock_post):
        
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
        
        response = await posts.create_post(posting_data=mock_post, db=db_session, request=mock_request)
        
        assert expected_output == response
        
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
        db_session.refresh.assert_called_once()
    
    
    @pytest.mark.parametrize("mock_is_start_before_end, mock_fetch_geocode_data, type, message, details, mock_location, mock_is_location_address", [
        (True, {"status": "error", "details": "Site not found"}, "OSM", "Site not found", None, "C/Test, 123", True),
        
        (False, {"status": "error", "details": "Site not found"}, "NewPost", "Invalid datetimes", "Starting date must be before ending date", "C/Test, 123", True),
        
        # (True, {"status": "error", "details": "Site not found"}, "OSM", "Site not found", None, [41.4567284, 23.8374634], False),
        
        (False, {"status": "error", "details": "Site not found"}, "NewPost", "Invalid datetimes", "Starting date must be before ending date", [41.4567284, 23.8374634], False),
    ])
    
    @pytest.mark.asyncio
    async def test_create_post_exceptions(self, mocker: MockerFixture, mock_request, message, details, mock_post, 
                                    mock_is_start_before_end, mock_fetch_geocode_data, type, mock_location, mock_is_location_address):
        
        db_session = mocker.Mock()
        
        mock_post.location = mock_location
        mocker.patch('app.routers.posts.time_utils.is_start_before_end', return_value=mock_is_start_before_end)
        mocker.patch('app.routers.posts.maps_utils.fetch_geocode_data', return_value=mock_fetch_geocode_data)
        mocker.patch('app.routers.posts.utils.is_location_address', return_value=mock_is_location_address)
        
        expected_error = {
            "status": "error",
            "message": message,
            "data": {
                "type": type,
                "message": message,
                "details": details
            },
            "meta": {
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type")
            }
        }
        
        with pytest.raises(HTTPException) as exception_data:
            await posts.create_post(posting_data=mock_post, db=db_session, request=mock_request)
        
        error_output = custom_http_exception_handler(mock_request, exception_data.value)
        error_body = error_output.body.decode("utf-8")
        error_response = json.loads(error_body)
        
        assert expected_error == error_response
    
    
    def test_nearby_events_succeed(self, mock_request, mocker: MockerFixture):
        
        db_session = mocker.Mock()
        
        mock_position = [41.273424, 23.872346]
        expected_output = schemas.SuccessResponse(
            status="success",
            message="Fetched event by distance",
            data={},
            meta={
                "request_id": mock_request.headers.get("request-id"), 
                "client": mock_request.headers.get("client-type")
            }
        )
        
        assert expected_output == True
        