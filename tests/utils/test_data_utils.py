import pytest
from pytest_mock import MockerFixture
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.schemas import InternalResponse, ResponseStatus
from app.models import Users
from app.utils.data_utils import (validate_email, 
                                  get_user_data, 
                                  get_code_owner)


class MockDatabaseSession:
    def __init__(self, mocker: MockerFixture):
        self.session = mocker.Mock()

    def mock_query_single_result(self, return_value):
        self.session.query().filter().first.return_value = return_value
        return self.session


class TestDataUtils:
    @pytest.fixture
    def mock_db_session(self, mocker: MockerFixture):
        return MockDatabaseSession(mocker).session

    @pytest.fixture
    def mock_db_user(self):
        return Users(
            id=1,
            full_name="User Test",
            email="test@example.com",
            password="uf3su4db48348734t834nn58",
            code=None,
            code_expiration=None,
            is_validated=True,
            created_at="2024-12-17 18:39:47.98487+01",
        )

    @pytest.fixture
    def expected_output_success(self):
        return InternalResponse(
            status=ResponseStatus.SUCCESS,
            origin="",
            message="",
            timestamp=datetime.now().isoformat(),
        )
    
    def test_validate_email_succeed(
        self, mock_db_session, mock_db_user: Users, expected_output_success: InternalResponse
    ):
        mock_db_session.query().filter().first.return_value = mock_db_user

        expected_output_success.status = ResponseStatus.SUCCESS
        expected_output_success.origin = "validate_email"
        expected_output_success.message = mock_db_user

        result = validate_email(mock_db_session, mock_db_user.email)
        expected_output_success.timestamp = result.timestamp

        assert result == expected_output_success
    
    def test_validate_email_errors(
        self, mock_db_session, mock_db_user: Users, expected_output_success: InternalResponse
    ):
        mock_db_session.query().filter().first.return_value = None

        expected_output_success.status = ResponseStatus.ERROR
        expected_output_success.origin = "validate_email"
        expected_output_success.message = "Not found"

        result = validate_email(mock_db_session, mock_db_user.email)
        expected_output_success.timestamp = result.timestamp

        assert result == expected_output_success
    
    def test_validate_email_exceptions(
        self, mock_db_session, mock_db_user: Users, expected_output_success: InternalResponse
    ):
        message = "Mocked raised error"
        mock_db_session.query().filter().first.side_effect = SQLAlchemyError(message)

        expected_output_success.status = ResponseStatus.ERROR
        expected_output_success.origin = "validate_email"
        expected_output_success.message = f"Database error raised: {message}"
        
        result: InternalResponse = validate_email(mock_db_session, mock_db_user.email)
        expected_output_success.timestamp = result.timestamp
        
        assert result == expected_output_success
    
    def test_get_user_data_succeed(
        self, mock_db_session, mock_db_user: Users, expected_output_success: InternalResponse
    ):
        mock_db_session.query().filter().first.return_value = mock_db_user

        expected_output_success.status = ResponseStatus.SUCCESS
        expected_output_success.origin = "get_user_data"
        expected_output_success.message = mock_db_user

        result = get_user_data(mock_db_session, mock_db_user.id)
        expected_output_success.timestamp = result.timestamp

        assert result == expected_output_success
    
    def test_get_user_data_errors(
        self, mock_db_session, mock_db_user: Users, expected_output_success: InternalResponse
    ):
        mock_db_session.query().filter().first.return_value = None

        expected_output_success.status = ResponseStatus.ERROR
        expected_output_success.origin = "get_user_data"
        expected_output_success.message = "Not found"

        result = get_user_data(mock_db_session, mock_db_user.id)
        expected_output_success.timestamp = result.timestamp

        assert result == expected_output_success
    
    def test_get_user_data_exceptions(
        self, mock_db_session, mock_db_user: Users, expected_output_success: InternalResponse
    ):
        message = "Mocked raised error"
        mock_db_session.query().filter().first.side_effect = SQLAlchemyError(message)

        expected_output_success.status = ResponseStatus.ERROR
        expected_output_success.origin = "get_user_data"
        expected_output_success.message = f"Database error raised: {message}"
        
        result: InternalResponse = get_user_data(mock_db_session, mock_db_user.email)
        expected_output_success.timestamp = result.timestamp
        
        assert result == expected_output_success
    
    def test_get_code_owner_succeed(
        self, 
        mock_db_session, 
        mock_db_user: Users, 
        expected_output_success: InternalResponse
    ):
        mock_db_session.query().filter().first.return_value = mock_db_user
        mock_db_user.code = 123456

        expected_output_success.status = ResponseStatus.SUCCESS
        expected_output_success.origin = "get_code_owner"
        expected_output_success.message = mock_db_user

        result = get_code_owner(mock_db_session, mock_db_user.code)
        expected_output_success.timestamp = result.timestamp

        assert result == expected_output_success
    
    def test_get_code_owner_errors(
        self, mock_db_session, mock_db_user: Users, expected_output_success: InternalResponse
    ):
        mock_db_session.query().filter().first.return_value = None
        mock_db_user.code = 123456

        expected_output_success.status = ResponseStatus.ERROR
        expected_output_success.origin = "get_code_owner"
        expected_output_success.message = "Not found"

        result = get_code_owner(mock_db_session, mock_db_user.code)
        expected_output_success.timestamp = result.timestamp

        assert result == expected_output_success
    
    def test_get_code_owner_exceptions(
        self, mock_db_session, mock_db_user: Users, expected_output_success: InternalResponse
    ):
        message = "Mocked raised error"
        mock_db_session.query().filter().first.side_effect = SQLAlchemyError(message)
        mock_db_user.code = 123456

        expected_output_success.status = ResponseStatus.ERROR
        expected_output_success.origin = "get_code_owner"
        expected_output_success.message = f"Database error raised: {message}"
        
        result: InternalResponse = get_code_owner(mock_db_session, mock_db_user.code)
        expected_output_success.timestamp = result.timestamp
        
        assert result == expected_output_success