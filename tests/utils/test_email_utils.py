import smtplib

import pytest
from pytest_mock import MockerFixture

import copy

from app.schemas.schemas import InternalResponse, ResponseStatus
from datetime import datetime
from app.services.retrieve_service import RetrieveService

from app.models import Users

import app.models as models
from app.utils import email_utils
from app.services.auth_service import AuthService
from app.utils.fetch_data_utils import validate_email

class MockEmailService:
    
    def __init__(self, mocker: MockerFixture):
        self.mocker = mocker
    
    def mock_send_email(self, return_value):
        return self.mocker.patch(
            "app.utils.email_utils.send_auth_code", return_value=return_value
        )
    
    def mock_smtp_error(self, side_effect):
        mock_smtp = self.mocker.patch("smtplib.SMTP")
        mock_smtp_instance = self.mocker.Mock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_instance.starttls.side_effect = side_effect
        return mock_smtp_instance

class MockDatabaseSession:
    
    def __init__(self, mocker: MockerFixture):
        self.mocker = mocker
        self.session = self.mocker.Mock()
    
    def mock_user_query(self, return_value):
        self.session.query().filter().first.return_value = return_value
        return self.session

class TestEmailUtils:

    @pytest.fixture
    def mock_db_session(self, mocker: MockerFixture):
        return MockDatabaseSession(mocker).session
    
    @pytest.fixture
    def mock_email_service(self, mocker: MockerFixture):
        return MockEmailService(mocker)
    
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
    def expected_output(self):
        return InternalResponse(
            status=ResponseStatus.SUCCESS,
            origin="",
            message="",
            timestamp=datetime.now().isoformat(),
        )

    def test_is_email_taken_succeed(
        self,
        mock_db_session,
        expected_output: InternalResponse,
        mocker: MockerFixture,
    ):
        fetched_email = "test2@example.es"
        
        validate_email_output = copy.deepcopy(expected_output)
        validate_email_output.status = ResponseStatus.ERROR
        validate_email_output.origin = "validate_email"
        validate_email_output.message = "Not found"

        expected_output.status = ResponseStatus.SUCCESS
        expected_output.origin = "is_email_taken"
        expected_output.message = "Email available"

        mocker.patch("app.utils.email_utils.validate_email", return_value=validate_email_output)
        
        result: InternalResponse = email_utils.is_email_taken(mock_db_session, fetched_email)
        expected_output.timestamp = result.timestamp

        assert result == expected_output

    @pytest.mark.parametrize(
        "fetched_email",
        [
            None,
            12345,
        ],
    )
    def test_is_email_taken_errors(
        self, 
        fetched_email, 
        mock_db_session,
        expected_output: InternalResponse
        ):
        
        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "is_email_taken"
        expected_output.message = "Email must be provided"

        result: InternalResponse = email_utils.is_email_taken(mock_db_session, fetched_email)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output

    def test_send_auth_code_succeed(
        self, 
        mocker: MockerFixture, 
        mock_db_session,
        expected_output: InternalResponse,
        mock_db_user: Users
        ):

        code = 123456
        expected_code_output = copy.deepcopy(expected_output)
        expected_send_email_output = copy.deepcopy(expected_output)
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.message = code
        expected_output.origin = "send_auth_code"
        
        expected_code_output.status = ResponseStatus.SUCCESS
        expected_code_output.message = code
        expected_code_output.origin = "generate_code"
        
        expected_send_email_output.status = ResponseStatus.SUCCESS
        expected_send_email_output.message = "Email sent"
        expected_send_email_output.origin = "send_email"
        
        mocker.patch.object(AuthService, 
                            expected_code_output.origin, 
                            return_value = expected_code_output)
        mocker.patch("app.utils.email_utils.send_email", 
                     return_value = expected_send_email_output)
        
        result: InternalResponse = email_utils.send_auth_code(mock_db_session, mock_db_user.email)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output

    @pytest.mark.parametrize("templateError, openFileError, sendEmailError, message", [
        (True, False, False, "HTML Template not found"),
        (False, True, False, "Email verification code template not found"),
        (False, False, True, "Failed to connect to the SMTP server"),
    ])
    def test_send_auth_code_errors(
        self, 
        mocker: MockerFixture, 
        mock_db_session,
        templateError,
        openFileError,
        sendEmailError,
        message,
        expected_output: InternalResponse,
        mock_db_user: Users
        ):

        template = 1
        code = 123456
        expected_code_output = copy.deepcopy(expected_output)
        
        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "send_auth_code"
        expected_output.message = message
        
        expected_code_output.status = ResponseStatus.SUCCESS
        expected_code_output.message = code
        expected_code_output.origin = "generate_code"
        
        mock_template_content = "email_verification_code.html"
        mocker.patch(
            "builtins.open", mocker.mock_open(read_data=mock_template_content)
        )
        mocker.patch.object(AuthService, "generate_code", return_value=expected_code_output)
        if templateError:
            template = 5
        if openFileError:
            mocker.patch("builtins.open", side_effect=FileNotFoundError)
        if sendEmailError:
            expected_output.origin = "send_email"
            mocker.patch("app.utils.email_utils.send_email", return_value=expected_output)
        mocker.patch("app.utils.email_utils.create_email_code_token", 
                     return_value={"email": mock_db_user.email, "code": code})
    
        result: InternalResponse = email_utils.send_auth_code(
            mock_db_session, 
            mock_db_user.email, 
            template
        )
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
        
    def test_send_updated_events_succeed(
        self, 
        mocker: MockerFixture, 
        mock_db_session,
        expected_output: InternalResponse,
        mock_db_user: Users
        ):

        expected_send_email_output = copy.deepcopy(expected_output)
        expected_get_user_data_output = copy.deepcopy(expected_output)
        
        mock_email_body = "<p> Test </p>"
        mock_changes = {"key": "Change"}
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.message = "Changes sent via email"
        expected_output.origin = "send_updated_events"
        
        expected_send_email_output.status = ResponseStatus.SUCCESS
        expected_send_email_output.message = "Email sent"
        expected_send_email_output.origin = "send_email"
        
        expected_get_user_data_output.status = ResponseStatus.SUCCESS
        expected_get_user_data_output.message = mock_db_user
        expected_get_user_data_output.origin = "get_user_data"
        
        mocker.patch("app.utils.email_utils.get_user_data", 
                     return_value=expected_get_user_data_output)
        mock_template_content = "event_changed.html"
        mocker.patch(
            "builtins.open", 
            mocker.mock_open(read_data=mock_template_content)
        )
        mocker.patch.object(RetrieveService, "generate_event_changes_html", 
                     return_value = mock_email_body)
        mocker.patch("app.utils.email_utils.send_email", 
                     return_value = expected_send_email_output)
        
        result: InternalResponse = email_utils.send_updated_events(mock_db_session, 
                                                                   mock_db_user.id,
                                                                   mock_changes)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
        
    @pytest.mark.parametrize(
        "getUserDataError, openFileError, sendEmailError, message",
        [
            (True, False, False, "Not found"),
            (False, True, False, "Updated Event template not found"),
            (False, False, True, "Failed to connect to the SMTP server"),
        ],
    )
    def test_send_updated_events_errors(
        self,
        mocker: MockerFixture,
        mock_db_session,
        expected_output: InternalResponse,
        mock_db_user: Users,
        getUserDataError,
        openFileError,
        sendEmailError,
        message,
    ):
        mock_email_body = "<p> Test </p>"
        mock_changes = {"key": "Change"}
        mock_template_content = "event_changed.html"

        expected_output.status = ResponseStatus.ERROR
        expected_output.message = message
        expected_output.origin = "send_updated_events"

        expected_send_email_output = copy.deepcopy(expected_output)
        expected_send_email_output.message = "Email sent"
        expected_send_email_output.origin = "send_email"

        expected_get_user_data_output = copy.deepcopy(expected_output)
        expected_get_user_data_output.message = mock_db_user
        expected_get_user_data_output.origin = "get_user_data"

        if getUserDataError:
            expected_get_user_data_output.status = ResponseStatus.ERROR
            expected_get_user_data_output.message = message
            expected_output.origin = expected_get_user_data_output.origin
        elif openFileError:
            expected_get_user_data_output.status = ResponseStatus.SUCCESS
            mocker.patch("builtins.open", side_effect=FileNotFoundError)
        else:
            mocker.patch(
                "builtins.open",
                mocker.mock_open(read_data=mock_template_content),
            )

        if sendEmailError:
            expected_send_email_output.status = ResponseStatus.ERROR
            expected_send_email_output.message = message
            expected_get_user_data_output.status = ResponseStatus.SUCCESS
            expected_get_user_data_output.message = mock_db_user
            expected_output.origin = expected_send_email_output.origin

        mocker.patch(
            "app.utils.email_utils.get_user_data",
            return_value=expected_get_user_data_output,
        )
        mocker.patch.object(
            RetrieveService,
            "generate_event_changes_html",
            return_value=mock_email_body,
        )
        mocker.patch(
            "app.utils.email_utils.send_email",
            return_value=expected_send_email_output,
        )

        result: InternalResponse = email_utils.send_updated_events(
            mock_db_session, mock_db_user.id, mock_changes
        )

        expected_output.timestamp = result.timestamp

        assert result == expected_output

        
    def test_send_email_succeed(
        self, 
        mocker: MockerFixture, 
        expected_output: InternalResponse,
        mock_db_user: Users):
        
        subject = "Test"
        html_content = "<p> Test </p)"
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.origin = "send_email"
        expected_output.message = "Email sent"
        
        mock_smtp = mocker.patch("smtplib.SMTP")
        mock_server = mock_smtp.return_value
        mock_server.starttls.return_value = None
        mock_server.login.return_value = None
        mock_server.sendmail.return_value = None
        mock_server.quit.return_value = None
        
        result = email_utils.send_email(mock_db_user.email, subject, html_content)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize(
        "_SMTPException, _ConnectionError, _GenericException, message", [
            (True, False, False, "SMTP error occurred"),
            (False, True, False, "Failed to connect to the SMTP server"),
            (False, False, True, "An unexpected error occurred"),
        ])
    def test_send_email_errors(
        self, 
        mocker: MockerFixture, 
        _SMTPException, 
        _ConnectionError, 
        _GenericException, 
        message,
        expected_output: InternalResponse,
        mock_db_user: Users):
        
        subject = "Test"
        html_content = "<p> Test </p)"
        
        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "send_email"
        detailError = ''
        
        mock_smtp = mocker.patch("smtplib.SMTP")
        mock_server = mock_smtp.return_value
        mock_server.starttls.return_value = None
        mock_server.login.return_value = None
        mock_server.sendmail.return_value = None
        mock_server.quit.return_value = None
        
        if _SMTPException:
             detailError = "SMTPError"
             mocker.patch("smtplib.SMTP", side_effect=smtplib.SMTPException(detailError))
        if _GenericException:
             detailError = "Test Exception"
             mocker.patch("smtplib.SMTP", side_effect=Exception(detailError))
        expected_output.message = f'{message}: {detailError}'
        if _ConnectionError:
             detailError = "Test Connection Failure"
             expected_output.message = message
             mocker.patch("smtplib.SMTP", side_effect=ConnectionError(detailError))
        
        result = email_utils.send_email(mock_db_user.email, subject, html_content)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
        
    def test_resend_auth_code_succeed(
        self, 
        mocker: MockerFixture,
        mock_db_session, 
        mock_db_user: Users,
        expected_output: InternalResponse):
        
        mock_db_user.code = 123456
        
        expected_output.status = ResponseStatus.SUCCESS
        expected_output.message="Email sent"
        expected_output.origin = "resend_auth_code"
        
        expected_owner_code_output = copy.deepcopy(expected_output)
        expected_owner_code_output.message = mock_db_user
        expected_owner_code_output.origin = "get_code_owner"

        expected_send_email_output = copy.deepcopy(expected_output)
        expected_send_email_output.message = "Email sent"
        expected_send_email_output.origin = "send_email"
        
        mocker.patch("app.utils.email_utils.get_code_owner", 
                     return_value=expected_owner_code_output)
        mocker.patch("app.utils.email_utils.send_auth_code", 
                     return_value=expected_send_email_output)
        
        result: InternalResponse = email_utils.resend_auth_code(mock_db_session, mock_db_user.code)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
    
    @pytest.mark.parametrize(
        "getCodeOwnerError, sendEmailError, message", [
            (True, False, "Not found"),
            (False, True, "Failed to connect to the SMTP server"),
        ])
    def test_resend_auth_code_errors(
        self, 
        mocker: MockerFixture,
        mock_db_session, 
        mock_db_user: Users,
        getCodeOwnerError, 
        sendEmailError, 
        message,
        expected_output: InternalResponse):
        
        mock_db_user.code = 123456
        
        expected_output.status = ResponseStatus.ERROR
        expected_output.origin = "resend_auth_code"

        expected_send_email_output = copy.deepcopy(expected_output)
        expected_send_email_output.message = "Email sent"
        expected_send_email_output.origin = "send_email"
        
        expected_owner_code_output = copy.deepcopy(expected_output)
        expected_owner_code_output.message = mock_db_user
        expected_owner_code_output.origin = "get_code_owner"
        
        expected_output.message=message
        
        if getCodeOwnerError:
            expected_owner_code_output.status = ResponseStatus.ERROR
            expected_owner_code_output.message = message
            expected_output.origin = expected_owner_code_output.origin
        
        if sendEmailError:
            expected_send_email_output.status = ResponseStatus.ERROR
            expected_send_email_output.message = message
            expected_output.origin = expected_send_email_output.origin
        
        mocker.patch("app.utils.email_utils.get_code_owner", 
                     return_value=expected_owner_code_output)
        mocker.patch("app.utils.email_utils.send_auth_code", 
                     return_value=expected_send_email_output)
        
        result: InternalResponse = email_utils.resend_auth_code(mock_db_session, mock_db_user.code)
        expected_output.timestamp = result.timestamp
        
        assert result == expected_output
        
    
