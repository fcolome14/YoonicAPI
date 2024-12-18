import pytest
from pytest_mock import MockerFixture
from fastapi import HTTPException
from app.schemas import schemas
from app.exception_handlers import custom_http_exception_handler
from app.routers import recall
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import json

class TestRecall:
    
    @pytest.fixture
    def mock_request(self, mocker: MockerFixture):
        mock_request = mocker.Mock()
        
        mock_request.headers = {
            "request-id": "default_request_id",
            "client-type": "unknown"
        }
        
        return mock_request
    
    def test_get_categories_success(self, mocker: MockerFixture, mock_request):
        db_session = mocker.Mock()
        
        mock_db_response = [
            (1, 'Sports', 'cat.1'), 
            (2, 'Culture', 'cat.2'), 
            (3, 'Tech', 'cat.3'), 
            (4, 'Media', 'cat.4'), 
            (5, 'Food', 'cat.5'), 
            (6, 'Travel', 'cat.6'), 
            (7, 'Fashion', 'cat.7'), 
            (8, 'Health & Wellness', 'cat.8')
            ]
        mock_expected_data = [{"id": row[0], "category": row[1], "code": row[2]} for row in mock_db_response]
        
        db_session.query().all.return_value = mock_db_response
        expected_output = schemas.SuccessResponse(
            status="success",
            message="Categories settings",
            data=mock_expected_data,
            meta={
                "request_id": mock_request.headers.get("request-id"), 
                "client": mock_request.headers.get("client-type")
            }
        )
        
        response = recall.get_categories(db_session, request=mock_request)
        
        assert expected_output == response
    
    def test_get_categories_exception(self, mocker: MockerFixture, mock_request):
        db_session = mocker.Mock()
        
        db_session.query().all.return_value = None
        expected_error = {
            "status": "error",
            "message": "Not Found",
            "data": {
                "type": "GetCategories",
                "message": "Not Found",
                "details": None
            },
            "meta": {
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type")
            }
        }
        
        with pytest.raises(HTTPException) as exception_data:
            recall.get_categories(db_session, request=mock_request)
        
        error_output = custom_http_exception_handler(mock_request, exception_data.value)
        error_body = error_output.body.decode("utf-8")
        error_response = json.loads(error_body)
        
        assert expected_error == error_response
    
    def test_get_tags_success(self, mocker: MockerFixture, mock_request):
        db_session = mocker.Mock()
        
        mock_db_response = [
            (251, 'Paris', 26,'subcat.6.1', 'Destinations'), 
            (252, 'New York City', 26, 'subcat.6.1', 'Destinations'), 
            (253, 'Tokyo', 26, 'subcat.6.1', 'Destinations'), 
            (254, 'Rome', 26, 'subcat.6.1', 'Destinations'), 
            (255, 'London', 26, 'subcat.6.1', 'Destinations'), 
            (300, 'Travel Blog', 30, 'subcat.6.5', 'Travel Photography')
            ]
        
        mock_expected_data = {
            "Destinations": [
                {
                    "subcategory_code": "subcat.6.1",
                    "tags": [
                        {"id": 251, "name": "Paris"},
                        {"id": 252, "name": "New York City"},
                        {"id": 253, "name": "Tokyo"},
                        {"id": 254, "name": "Rome"},
                        {"id": 255, "name": "London"}
                    ]
                }
            ],
            "Travel Photography": [
                {
                    "subcategory_code": "subcat.6.5",
                    "tags": [
                        {"id": 300, "name": "Travel Blog"}
                    ]
                }
            ]
        }

        db_session.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = mock_db_response
        expected_output = schemas.SuccessResponse(
            status="success",
            message="Tags",
            data=mock_expected_data,
            meta={
                "request_id": mock_request.headers.get("request-id"), 
                "client": mock_request.headers.get("client-type")
            }
        )
        
        response = recall.get_tags(3, db_session, request=mock_request)
        
        assert expected_output == response
    
    def test_get_tags_exception(self, mocker: MockerFixture, mock_request):
        db_session = mocker.Mock()
        
        db_session.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = None
        expected_error = {
            "status": "error",
            "message": "Not Found",
            "data": {
                "type": "GetTags",
                "message": "Not Found",
                "details": None
            },
            "meta": {
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type")
            }
        }
        
        with pytest.raises(HTTPException) as exception_data:
            recall.get_tags(3, db_session, request=mock_request)
        
        error_output = custom_http_exception_handler(mock_request, exception_data.value)
        error_body = error_output.body.decode("utf-8")
        error_response = json.loads(error_body)
        
        assert expected_error == error_response