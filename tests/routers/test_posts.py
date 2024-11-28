import pytest
from pytest_mock import MockerFixture
from fastapi import HTTPException
from app.schemas import schemas
import app.models
from app.exception_handlers import custom_http_exception_handler
from app.routers import posts
from datetime import datetime, timezone
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
        
    @pytest.mark.skip    
    def test_create_post_succeed(self, mocker: MockerFixture, mock_request):
        
        db_session = mocker.Mock()
        
        fetched_data = schemas.NewPostInput(
            title = "Test",
            description = None,
            start = datetime.now(timezone.utc),
            end = datetime.now(timezone.utc),
            location = "C/Test, 123",
            is_public = True,
            category = 1,
            tags = None,
            cost = 0,
            currency = None,
            capacity =None
        )
        expected_output = schemas.SuccessResponse(
            status="success",
            message="New event created",
            data={},
            meta={
                "request_id": mock_request.headers.get("request-id"), 
                "client": mock_request.headers.get("client-type")
            }
        )
        
        response = posts.create_post(post_data=fetched_data, db=db_session, user_id=1, request=mock_request)
        
        assert expected_output == response
    
    @pytest.mark.parametrize("token_auth, message, details", [
        (1, "Invalid datetimes", "Starting date must be before ending date"),
    ])
    
    @pytest.mark.skip
    def test_create_post_exceptions(self, mocker: MockerFixture, mock_request, message, details, token_auth):
        
        db_session = mocker.Mock()
        
        fetched_data = schemas.NewPostInput(
            title = "Test",
            description = None,
            start = datetime.now(timezone.utc),
            end = datetime.now(timezone.utc),
            location = "C/Test, 123",
            is_public = True,
            category = 1,
            tags = None,
            cost = 0,
            currency = None,
            capacity = None
        )
        
        # mocker.patch('app.routers.auth.get_db', return_value=db_session)
        # mocker.patch('app.routers.auth.utils.is_password_valid', return_value=is_password_valid)
        # mocker.patch('app.routers.auth.utils.is_user_logged', return_value=is_user_logged)
        # db_session.query().filter().first.return_value = user
        
        expected_error = {
            "status": "error",
            "message": message,
            "data": {
                "type": "NewPost",
                "message": message,
                "details": details
            },
            "meta": {
                "request_id": mock_request.get("request-id"),
                "client": mock_request.get("client-type")
            }
        }
        
        with pytest.raises(HTTPException) as exception_data:
            posts.create_post(post_data=fetched_data, db=db_session, user_id=token_auth, request=mock_request)
        
        error_output = custom_http_exception_handler(mock_request, exception_data.value)
        error_body = error_output.body.decode("utf-8")
        error_response = json.loads(error_body)
        
        assert expected_error == error_response