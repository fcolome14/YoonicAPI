import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from pytest_mock import MockerFixture

import app.models as models
import app.oauth2 as oauth2
import app.schemas as schemas
from app.config import settings
from app.exception_handlers import custom_http_exception_handler
from app.routers.auth import (login, password_recovery_code, refresh_code,
                              register_user, verify_code)

templates = Jinja2Templates(directory="app/templates")


@pytest.fixture
def mock_credentials():
    return OAuth2PasswordRequestForm(username="texample", password="123456")


class TestAuth:
    """Auth methods tests"""

    @pytest.fixture(autouse=True)
    def mock_db_session(self, mocker: MockerFixture):
        mock_session = mocker.Mock()

        mock_user = models.Users(
            id=1,
            email="test@example.com",
            password="hashed_password",
            full_name="Test Example",
            username="texample",
            code=123456,
            is_validated=True,
            code_expiration=datetime.now(timezone.utc),
        )

        mock_session.query().filter().first.return_value = mock_user

        return mock_session, mock_user

    @pytest.fixture
    def mock_request(self, mocker: MockerFixture):
        mock_request = mocker.Mock()

        mock_request.headers = {
            "request-id": "default_request_id",
            "client-type": "unknown",
        }

        return mock_request

    def test_login_success(
        self, mocker: MockerFixture, mock_db_session, mock_credentials, mock_request
    ):

        db_session, user = mock_db_session

        mocker.patch("app.routers.auth.get_db", return_value=db_session)
        mocker.patch("app.routers.auth.utils.is_password_valid", return_value=True)
        # mocker.patch('app.routers.auth.utils.is_user_logged', return_value=False)
        mock_access_token = "mocked_access_token"
        mock_refresh_token = "mocked_refresh_token"
        mocker.patch(
            "app.routers.auth.oauth2.create_access_token",
            return_value=mock_access_token,
        )
        mocker.patch(
            "app.routers.auth.oauth2.create_refresh_token",
            return_value=mock_refresh_token,
        )

        expected_output = schemas.SuccessResponse(
            status="success",
            message="Login succeed",
            data={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "token": mock_access_token,
            },
            meta={
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type"),
            },
        )

        response = login(
            user_credentials=mock_credentials, db=db_session, request=mock_request
        )

        assert response == expected_output

    @pytest.mark.parametrize(
        "is_user_logged, is_password_valid, user, details, message",
        [
            # (True, True, models.Users(
            #     id=1,
            #     email="test@example.com",
            #     password="hashed_password",
            #     full_name="Test Example",
            #     username="texample",
            #     is_validated=True),
            #  None,
            #  "User already logged in"),
            # (True, False, models.Users(
            #     id=1,
            #     email="test@example.com",
            #     password="hashed_password",
            #     full_name="Test Example",
            #     username="texample",
            #     is_validated=True),  None, "User already logged in"),
            (
                False,
                False,
                models.Users(
                    id=1,
                    email="test@example.com",
                    password="hashed_password",
                    full_name="Test Example",
                    username="texample",
                    is_validated=True,
                ),
                "Invalid password",
                "Invalid Credentials",
            ),
            (False, True, False, "User not found", "Invalid Credentials"),
        ],
    )
    def test_login_exceptions(
        self,
        mocker: MockerFixture,
        mock_db_session,
        mock_credentials,
        mock_request,
        is_user_logged,
        is_password_valid,
        message,
        details,
        user,
    ):

        db_session, _ = mock_db_session

        mocker.patch("app.routers.auth.get_db", return_value=db_session)
        mocker.patch(
            "app.routers.auth.utils.is_password_valid", return_value=is_password_valid
        )
        # # mocker.patch('app.routers.auth.utils.is_user_logged', return_value=is_user_logged)
        db_session.query().filter().first.return_value = user

        expected_error = {
            "status": "error",
            "message": message,
            "data": {"type": "Auth", "message": message, "details": details},
            "meta": {
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type"),
            },
        }

        with pytest.raises(HTTPException) as exception_data:
            login(
                user_credentials=mock_credentials, db=db_session, request=mock_request
            )

        error_output = custom_http_exception_handler(mock_request, exception_data.value)
        error_body = error_output.body.decode("utf-8")
        error_response = json.loads(error_body)

        assert expected_error == error_response

    def test_register_succeed(
        self, mocker: MockerFixture, mock_db_session, mock_request
    ):
        """User register test success"""

        db_session, user = mock_db_session

        db_session.query().filter().first.return_value = None
        mocker.patch("app.routers.auth.utils.is_account_unverified", return_value=None)
        mocker.patch(
            "app.routers.auth.utils.is_username_email_taken", return_value=None
        )
        mocker.patch("app.routers.auth.utils.is_password_strong", return_value=True)
        mocker.patch(
            "app.routers.auth.email_utils.send_auth_code",
            return_value={"status": "success", "message": 123456},
        )
        mock_hashed_password = "hashed_testpassword"
        mocker.patch(
            "app.routers.auth.utils.hash_password", return_value=mock_hashed_password
        )

        user_input = schemas.RegisterInput(
            email=user.email,
            username=user.username,
            password="test_password",
            full_name="Test Example",
        )

        expected_output = schemas.SuccessResponse(
            status="success",
            message="Account pending validation",
            data={},
            meta={
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type"),
            },
        )

        response = register_user(user_input, db_session, mock_request)

        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()

        assert expected_output == response

    @pytest.mark.parametrize(
        "fetched_data, mocked_function, mock_value, message, details",
        [
            (
                schemas.RegisterInput(
                    username="testuser",
                    full_name="Test User",
                    email="testuser@example.com",
                    password="testpassword123",
                ),
                "utils.is_account_unverified",
                True,
                "Unverified account",
                "An account with 'testuser@example.com' or 'testuser' exists but is not verified yet",
            ),
            (
                schemas.RegisterInput(
                    username="testuser",
                    full_name="Test User",
                    email="testuser@example.com",
                    password="",
                ),
                "utils.is_username_email_taken",
                True,
                "Username or Email already exists",
                "Username 'testuser' or 'testuser@example.com' is already taken",
            ),
            (
                schemas.RegisterInput(
                    username="testuser",
                    full_name="Test User",
                    email="testuser@example.com",
                    password="",
                ),
                "utils.is_password_strong",
                False,
                "Weak password",
                None,
            ),
            (
                schemas.RegisterInput(
                    username="testuser",
                    full_name="Test User",
                    email="testuser@example.com",
                    password="123",
                ),
                "utils.is_password_strong",
                False,
                "Weak password",
                None,
            ),
            (
                schemas.RegisterInput(
                    username="testuser",
                    full_name="Test User",
                    email="testuser@example.com",
                    password="testpassword123",
                ),
                "email_utils.send_auth_code",
                {
                    "status": "error",
                    "message": "Email verification code template not found",
                },
                "Email verification code template not found",
                "Sending validation email",
            ),
        ],
    )
    def test_register_exceptions(
        self,
        mocker: MockerFixture,
        fetched_data,
        mocked_function,
        mock_value,
        message,
        details,
        mock_request,
        mock_db_session,
    ):
        """Register user test raised exceptions"""

        db_session, _ = mock_db_session

        db_session.query().filter().first.return_value = None
        mocker.patch("app.routers.auth.utils.is_account_unverified", return_value=None)
        mocker.patch(
            "app.routers.auth.utils.is_username_email_taken", return_value=False
        )
        mocker.patch("app.routers.auth.utils.is_password_strong", return_value=True)
        mocker.patch(
            "app.routers.auth.email_utils.send_auth_code",
            return_value={"status": "success", "message": 123456},
        )

        mocker.patch(f"app.routers.auth.{mocked_function}", return_value=mock_value)

        expected_error = {
            "status": "error",
            "message": message,
            "data": {"type": "Register", "message": message, "details": details},
            "meta": {
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type"),
            },
        }

        with pytest.raises(HTTPException) as exception_data:
            register_user(
                user_credentials=fetched_data, db=db_session, request=mock_request
            )

        error_output = custom_http_exception_handler(mock_request, exception_data.value)
        error_body = error_output.body.decode("utf-8")
        error_response = json.loads(error_body)

        assert expected_error == error_response

    def test_verify_code_succeed(
        self, mocker: MockerFixture, mock_db_session, mock_request
    ):
        """Verification code test succeed case"""

        db_session, user = mock_db_session
        data = {"email": user.email, "code": 123456}
        fetched_data = oauth2.create_email_code_token(data)

        mock_is_code_valid_result = {"status": "success", "details": "Verified code"}
        mock_decode_email_code_token = mocker.patch(
            "app.routers.auth.oauth2.decode_email_code_token",
            return_value={"status": "success", "message": data},
        )
        mocker.patch(
            "app.routers.auth.utils.is_code_valid",
            return_value=mock_is_code_valid_result,
        )
        mock_user_query = mocker.patch.object(db_session, "query")
        mock_user_query.return_value.filter.return_value.first.return_value = user
        mock_setting_email = mocker.patch(
            "app.config.settings.email", return_value=user.email
        )

        expected_output = templates.TemplateResponse(
            "code_verification_result.html",
            {
                "request": mock_request,
                "message": mock_is_code_valid_result.get(
                    "details", "Your verification was successful!"
                ),
                "email": mock_setting_email,
                "success": (
                    True
                    if mock_is_code_valid_result.get("status") == "success"
                    else False
                ),
            },
        ).body.decode("utf-8")

        response = verify_code(token=fetched_data, db=db_session, request=mock_request)

        mock_decode_email_code_token.assert_called_once_with(fetched_data)

        assert response.body.decode("utf-8").strip() == expected_output.strip()

    @pytest.mark.parametrize(
        "expected_message",
        [
            {"status": "error", "details": "Code not found"},
            {"status": "error", "details": "Expired code"},
        ],
    )
    def test_verify_code_errors(
        self, mocker: MockerFixture, mock_db_session, mock_request, expected_message
    ):
        """Verification code test errors case"""

        db_session, user = mock_db_session
        data = {"email": user.email, "code": 123456}
        fetched_data = oauth2.create_email_code_token(data)

        mock_decode_email_code_token = mocker.patch(
            "app.routers.auth.oauth2.decode_email_code_token",
            return_value={"status": "success", "message": data},
        )
        mocker.patch(
            "app.routers.auth.utils.is_code_valid", return_value=expected_message
        )
        mock_user_query = mocker.patch.object(db_session, "query")
        mock_user_query.return_value.filter.return_value.first.return_value = (
            user if expected_message.get("status") == "success" else None
        )

        expected_output = templates.TemplateResponse(
            "code_verification_result.html",
            {
                "request": mock_request,
                "message": expected_message.get(
                    "details", "Your verification was successful!"
                ),
                "email": data.get("email"),
                "success": (
                    True if expected_message.get("status") == "success" else False
                ),
            },
        ).body.decode("utf-8")

        response = verify_code(token=fetched_data, db=db_session, request=mock_request)

        mock_decode_email_code_token.assert_called_once_with(fetched_data)

        assert response.body.decode("utf-8").strip() == expected_output.strip()

    @pytest.mark.parametrize(
        "expected_exception, expiration_time, data",
        [
            (
                {
                    "message": "An unexpected error occurred: Signature has expired.",
                    "details": None,
                },
                datetime.now() - timedelta(hours=1),
                {"email": "test@example.com", "code": 123456},
            ),
            (
                {"message": "Invalid token", "details": None},
                "2024-11-25 13:55:11.905361",
                {"email": "test@example.com", "code": 123456},
            ),
        ],
    )
    def test_verify_code_exceptions(
        self,
        mocker: MockerFixture,
        mock_db_session,
        expected_exception,
        expiration_time,
        data,
        mock_request,
    ):

        db_session, _ = mock_db_session
        mocker.patch(
            "app.routers.auth.oauth2.decode_email_code_token",
            return_value={
                "status": "error",
                "message": expected_exception.get("message"),
            },
        )

        data["exp"] = expiration_time
        fetched_data = jwt.encode(data, settings.secret_key, settings.algorithm)

        expected_error = {
            "status": "error",
            "message": expected_exception.get("message"),
            "data": {
                "type": "VerifyCode",
                "message": expected_exception.get("message"),
                "details": None,
            },
            "meta": {
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type"),
            },
        }

        if expected_exception["message"] == "Invalid token":
            fetched_data = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNzMyNTQzMzAwLCJpYXQiOjE3MzI1Mzk3MDB9.RgxOUQi5EHhywkNueI96_1IRM70F4T-uSLJRmjlM6Go"

        with pytest.raises(HTTPException) as exception:
            verify_code(fetched_data, db_session)

        error_output = custom_http_exception_handler(mock_request, exception.value)
        error_body = error_output.body.decode("utf-8")
        error_response = json.loads(error_body)

        assert expected_error == error_response

    def test_refresh_code_succeed(
        self, mocker: MockerFixture, mock_db_session, mock_request
    ):
        """Refreshing code test success"""

        db_session, user = mock_db_session

        mock_value = {"status": "success", "new_code": user.code, "user": user}
        mocker.patch("app.routers.auth.utils.is_code_expired", return_value=False)
        mocker.patch(
            "app.routers.auth.email_utils.resend_auth_code", return_value=mock_value
        )

        expected_output = schemas.SuccessResponse(
            status="success",
            message="CodeRefresh",
            data={},
            meta={
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type"),
            },
        )

        response = refresh_code(db_session, mock_request, mock_request)

        assert response == expected_output

    @pytest.mark.parametrize(
        "message, mock_is_code_expired",
        [
            ("Code not found", False),
            ("User not found", False),
            ("Previous requested code is still active", True),
        ],
    )
    def test_refresh_code_exceptions(
        self,
        mocker: MockerFixture,
        mock_db_session,
        mock_request,
        message,
        mock_is_code_expired,
    ):
        """Refreshing code test including success and failures"""

        db_session, user = mock_db_session

        if message == "User not found":
            db_session.query().filter().first.return_value = None
        fetched_data = schemas.CodeValidationInput(code=123456, email=user.email)
        mocker.patch(
            "app.routers.auth.utils.is_code_expired", return_value=mock_is_code_expired
        )
        mocker.patch(
            "app.routers.auth.email_utils.resend_auth_code",
            return_value={"status": "error", "message": message},
        )

        expected_error = {
            "status": "error",
            "message": message,
            "data": {"type": "RefreshCode", "message": message, "details": None},
            "meta": {
                "request_id": mock_request.headers.get("request-id"),
                "client": mock_request.headers.get("client-type"),
            },
        }

        with pytest.raises(HTTPException) as exception_data:
            refresh_code(
                email_refresh=fetched_data, db=db_session, request=mock_request
            )

        error_output = custom_http_exception_handler(mock_request, exception_data.value)
        error_body = error_output.body.decode("utf-8")
        error_response = json.loads(error_body)

        assert error_response == expected_error

    def test_password_recovery_code_succeed(
        self, mocker: MockerFixture, mock_db_session, mock_request
    ):

        db_session, user = mock_db_session

        fetched_data = schemas.RecoveryCodeInput(email=user.email)

        mock_value = {"status": "success", "message": user.code}
        db_session.query().filter().first.return_value = user
        mocker.patch(
            "app.routers.auth.email_utils.send_auth_code", return_value=mock_value
        )

        expected_output = schemas.SuccessResponse(
            status="success",
            message="Account recovery validation sent",
            data={},
            meta={
                "request_id": mock_request.headers.get(
                    "request-id", "default_request_id"
                ),
                "client": mock_request.headers.get("client-type", "unknown"),
            },
        )

        response = password_recovery_code(fetched_data, db_session, mock_request)

        assert response == expected_output

    @pytest.mark.parametrize(
        "user, mock_value, details",
        [
            (
                models.Users(
                    id=1,
                    username="testuser",
                    full_name="Test User",
                    email="testuser@example.com",
                    password="testpassword123",
                ),
                {"status": "error", "message": "Failed to connect to the SMTP server"},
                "Sending validation email for password recovery code",
            ),
        ],
    )
    def test_password_recovery_code_exceptions(
        self,
        mocker: MockerFixture,
        user,
        mock_value,
        details,
        mock_request,
        mock_db_session,
    ):
        """Password recovery test raised exceptions"""

        db_session, _ = mock_db_session
        mocker.patch(
            "app.routers.auth.email_utils.send_auth_code", return_value=mock_value
        )

        expected_error = {
            "status": "error",
            "message": mock_value["message"],
            "data": {
                "type": "RecoveryCode",
                "message": mock_value["message"],
                "details": details,
            },
            "meta": {
                "request_id": mock_request.headers.get(
                    "request-id", "default_request_id"
                ),
                "client": mock_request.headers.get("client-type", "unknown"),
            },
        }

        with pytest.raises(HTTPException) as exception_data:
            password_recovery_code(
                schemas.RecoveryCodeInput(email=user.email), db_session, mock_request
            )

        error_output = custom_http_exception_handler(mock_request, exception_data.value)
        error_body = error_output.body.decode("utf-8")
        error_response = json.loads(error_body)

        assert expected_error == error_response
