import pytest
from fastapi import HTTPException
from app.routers.auth import login, register_user, verify_code, refresh_code, password_recovery
from pytest_mock import MockerFixture
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
import app.models as models
import app.schemas as schemas
from app.utils import utils, email_utils
import app.oauth2 as oauth2
from datetime import datetime

@pytest.fixture
def mock_credentials():
    return OAuth2PasswordRequestForm(username="test@example.com", password="123456")

class TestAuth:
    """Authorization tests"""

    @pytest.fixture(autouse=True)
    def mock_db_session(self, mocker: MockerFixture):
        mock_session = mocker.Mock()

        mock_user = models.Users(
            id=1, 
            email="test@example.com", 
            password="hashed_password", 
            full_name="Test Example", 
            username="texample"
            )
        
        mock_session.query().filter().first.return_value = mock_user

        return mock_session
    
    def test_login_succeed(self, mock_credentials, mock_db_session, mocker):
        """ Login succeed test """
        
        mocker.patch.object(utils, "is_password_valid", return_value=True)

        mock_token = "mocked_jwt_token"
        mocker.patch.object(oauth2, "create_access_token", return_value=mock_token)

        result = login(mock_credentials, mock_db_session)

        assert result == {"access_token": mock_token, "token_type": "bearer"}

    def test_login_user_not_found(self, mock_credentials, mock_db_session):
        """ Login user not found test """
        
        mock_db_session.query().filter().first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            login(mock_credentials, mock_db_session)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Invalid Credentials"

    def test_login_invalid_password(self, mock_credentials, mock_db_session, mocker):
        """ Login invalid password test """
        
        mocker.patch.object(utils, "is_password_valid", return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            login(mock_credentials, mock_db_session)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Invalid Credentials"
    
    @pytest.mark.parametrize(
        "fetched_data, expected_result",
        [
            (schemas.RegisterUser(username="testuser",full_name="Test User",email="testuser@example.com",password="testpassword"),
             schemas.GetUsers(username="testuser",email="testuser@example.com",full_name="Test User")
             )
        ]
    )
    def test_register_succeed(self, mocker: MockerFixture, fetched_data, expected_result):
        
        mock_session = mocker.Mock()
        
        mock_session.query().filter().first.return_value = None
        mocker.patch("app.routers.auth.utils.is_account_unverified", return_value=None)
        mocker.patch("app.routers.auth.email_utils.is_email_valid", return_value=fetched_data.email)
        mocker.patch("app.routers.auth.email_utils.is_email_taken", return_value=None)
        mocker.patch("app.routers.auth.utils.is_username_taken", return_value=None)
        mocker.patch("app.routers.auth.utils.is_password_strong", return_value=True)
        
        mock_hashed_password = "hashed_testpassword"
        mocker.patch("app.routers.auth.utils.hash_password", return_value=mock_hashed_password)
        
        mocker.patch("app.routers.auth.email_utils.send_validation_email", return_value={"validation_code": 123456, "status": 200})
        
        response = register_user(fetched_data, mock_session)
        
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
        response_json = schemas.GetUsers(
            username = response.username,
            email = response.email,
            full_name = response.full_name,
        )

        assert expected_result == response_json

    @pytest.mark.parametrize(
        "fetched_data, mocked_function, mock_value, expected_exception, expected_status_code, expected_type, expected_message",
        [
            (schemas.RegisterUser(username="testuser",full_name="Test User",email="testuser@example.com",password="testpassword123"),
             "utils.is_account_unverified", True, HTTPException, 400, "UnverifiedAccount", "An account with this email or username exists but is not verified."
             ),
            
            (schemas.RegisterUser(username="testuser",full_name="Test User",email="testuser@example.com",password=""),
             "utils.is_password_strong", False, HTTPException, 409, 
             "WeakPassword", "Weak password"
             ),
            
            (schemas.RegisterUser(username="testuser",full_name="Test User",email="testuser@example.com",password="123"),
              "utils.is_password_strong", False, HTTPException, 409, 
             "WeakPassword", "Weak password"
             ),
            
            (schemas.RegisterUser(username="testuser",full_name="Test User",email="testuser@example.com",password="testpassword123"),
             "email_utils.send_validation_email", {"status": 500, "message": "Internal error"}, HTTPException, 500, "ValidationEmailError", "Internal error"
             ),
        ]
    )
    def test_register_exceptions(self, mocker: MockerFixture, fetched_data, mocked_function, mock_value, 
                                      expected_exception, expected_status_code, expected_type, expected_message):
        
        mock_session = mocker.Mock()
        
        mock_session.query().filter().first.return_value = None
        mocker.patch("app.routers.auth.utils.is_account_unverified", return_value=None)
        mocker.patch("app.routers.auth.email_utils.is_email_valid", return_value="testuser@example.com")
        mocker.patch("app.routers.auth.email_utils.is_email_taken", return_value=False)
        mocker.patch("app.routers.auth.utils.is_username_taken", return_value=False)
        mocker.patch("app.routers.auth.utils.is_password_strong", return_value=True)
        mocker.patch("app.routers.auth.email_utils.send_validation_email", return_value={"status": 200, "validation_code": 123456})
        
        mocker.patch(f"app.routers.auth.{mocked_function}", return_value=mock_value)
        
        with pytest.raises(expected_exception) as exc_info:
            register_user(fetched_data, mock_session)

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail["type"] == expected_type
        assert exc_info.value.detail["message"] == expected_message
        

    @pytest.mark.parametrize("is_code_valid, user_found", [(True, True), (True, False), (False, None)])
    def test_verify_code(self, mocker: MockerFixture, is_code_valid, user_found):
        
        mock_db_session = mocker.Mock()
        fetched_data = schemas.CodeValidation(code=123456, is_password_recovery=False)

        mocker.patch("app.routers.auth.utils.is_code_valid", return_value=is_code_valid)

        if user_found:
            mock_user = mocker.Mock(spec=models.Users)
            mock_user.is_validated = False
            mock_user.code = 123456
            mock_user.code_expiration = None
            mock_db_session.query().filter().first.return_value = mock_user
        else:
            mock_db_session.query().filter().first.return_value = None

        if not is_code_valid:
            with pytest.raises(HTTPException) as exc_info:
                verify_code(fetched_data, mock_db_session)

            assert exc_info.value.status_code == 401
            assert exc_info.value.detail["type"] == "InvalidToken"
            assert exc_info.value.detail["message"] == "Invalid or expired token"

        elif not user_found:
            with pytest.raises(AttributeError):
                verify_code(fetched_data, mock_db_session)

        else:
            response = verify_code(fetched_data, mock_db_session)

            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

            mock_user.is_validated = True
            mock_user.code = None
            mock_user.code_expiration = None

            assert response == {"message": "code verified"}


    @pytest.mark.parametrize("resend_email_response, user_found, expected_exception", [
        ({"result": 654321, "user_email": "user@example.com"}, True, None),  # Test Success
        ({"error": "Email not sent", "status": 500}, True, HTTPException),   # Test Error in email resend
        ({"result": 654321, "user_email": "user@example.com"}, False, HTTPException),  # Test User not found
            ])
    def test_refresh_code(self, mocker:MockerFixture, resend_email_response, user_found, expected_exception):

        mock_db_session = mocker.Mock()
        email_refresh = schemas.CodeValidation(code=123456, is_password_recovery=False)
        mocker.patch("app.routers.auth.email_utils.resend_email", return_value=resend_email_response)

        if user_found:
            mock_user = mocker.Mock(spec=models.Users)
            mock_user.email = "user@example.com"
            mock_user.is_validated = False
            mock_db_session.query().filter().first.return_value = mock_user
        else:
            mock_db_session.query().filter().first.return_value = None

        if "error" in resend_email_response:
            with pytest.raises(HTTPException) as exc_info:
                refresh_code(email_refresh, mock_db_session)

            assert exc_info.value.status_code == resend_email_response["status"]
            assert exc_info.value.detail["type"] == "ValidationEmailError"
            assert exc_info.value.detail["message"] == resend_email_response["error"]

        elif not user_found:
            with pytest.raises(HTTPException) as exc_info:
                refresh_code(email_refresh, mock_db_session)

            assert exc_info.value.status_code == 404
            assert str(exc_info.value.detail) == "User not found or already verified"

        else:
            response = refresh_code(email_refresh, mock_db_session)

            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

            assert mock_user.code == resend_email_response["result"]
            assert mock_user.code_expiration is not None
            assert response == mock_user
    
    @pytest.mark.parametrize("email_response, user_found, expected_exception", [
    ({"status": 200, "message": "Recovery email sent"}, True, None),  # Test Success
    ({"status": 500, "message": "Email service unavailable"}, True, HTTPException),  # Test Email failure
    ({"status": 200, "message": "Recovery email sent"}, False, HTTPException),  # Test User not found
        ])
    @pytest.mark.skipif
    def test_password_recovery(self, mocker: MockerFixture, email_response, user_found, expected_exception):
        
        mock_db_session = mocker.Mock()
        user_credentials = schemas.PasswordRecovery(email="user@example.com")

        mocker.patch("app.routers.auth.email_utils.send_recovery_email", return_value=email_response)

        if user_found:
            mock_user = mocker.Mock(spec=models.Users)
            mock_user.email = "user@example.com"
            mock_user.password_recovery = False
            mock_db_session.query().filter().first.return_value = mock_user
        else:
            mock_db_session.query().filter().first.return_value = None

        if "status" in email_response and email_response["status"] != 200:
            with pytest.raises(HTTPException) as exc_info:
                password_recovery(user_credentials, mock_db_session)

            assert exc_info.value.status_code == email_response["status"]
            assert exc_info.value.detail["type"] == "ValidationEmailError"
            assert exc_info.value.detail["message"] == email_response["message"]

        elif not user_found:
            with pytest.raises(HTTPException) as exc_info:
                password_recovery(user_credentials, mock_db_session)

            assert exc_info.value.status_code == 404
            assert str(exc_info.value.detail) == "User not found"

        else:
            response = password_recovery(user_credentials, mock_db_session)

            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()
            
            mock_user.password_recovery = False
            
            assert mock_user.code_expiration is not None
            assert response == mock_user