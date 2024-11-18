import pytest
from fastapi import HTTPException
from app.utils import email_utils
from pytest_mock import MockerFixture
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
import app.models as models
import app.schemas as schemas
from app.utils import utils, email_utils
import app.oauth2 as oauth2
from datetime import datetime

class TestEmailUtils:
    
    @pytest.mark.parametrize("fetched_email, expected_output", [
        ("example2@test.com", None),
        ("example@test.com",
        models.Users(
            id = 1,
            username = "example",
            full_name = "Example Test",
            email = "example@test.com",
            password = "hashed_password",
            is_validated = False
        )
        ),
        ])
    
    def test_is_email_taken(self, mocker: MockerFixture, expected_output, fetched_email):
        
        mock_db_session = mocker.Mock()
        mock_db_session.query().filter().first.return_value = expected_output
        
        response = email_utils.is_email_taken(mock_db_session, fetched_email)
        
        assert response == expected_output
    
    
    @pytest.mark.parametrize("fetched_email", [None, 12345,])

    def test_is_email_taken_exceptions(self, mocker: MockerFixture, fetched_email):
        
        mock_db_session = mocker.Mock()
        mock_db_session.query().filter().first.return_value = None
        
        with pytest.raises(ValueError):
            email_utils.is_email_taken(mock_db_session, fetched_email)
        
        