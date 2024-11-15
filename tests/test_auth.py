import pytest
from fastapi import HTTPException
from app.routers.auth import login
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
import app.models as models
import app.utils as utils
import app.oauth2 as oauth2

@pytest.fixture
def mock_credentials():
    return OAuth2PasswordRequestForm(username="test@example.com", password="123456")

class TestAuth:
    """Authorization tests"""

    @pytest.fixture
    def mock_db_session(self, mocker):
        mock_session = mocker.Mock()

        mock_user = models.Users(id=1, email="test@example.com", password="hashed_password")
        mock_session.query().filter().first.return_value = mock_user

        return mock_session

    def test_login_succeed(self, mock_credentials, mock_db_session, mocker):
        """ Login succeed test """
        
        mocker.patch.object(utils, "verify", return_value=True)

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
        
        mocker.patch.object(utils, "verify", return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            login(mock_credentials, mock_db_session)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Invalid Credentials"
