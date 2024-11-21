import pytest
from app.utils import email_utils
from pytest_mock import MockerFixture
from email_validator import EmailUndeliverableError
import app.models as models
from app.utils import email_utils

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
        """ Test if email is taken for different invalid inputs """
        
        mock_db_session = mocker.Mock()
        mock_db_session.query().filter().first.return_value = expected_output
        
        response = email_utils.is_email_taken(mock_db_session, fetched_email)
        
        assert response == expected_output
    
    
    @pytest.mark.parametrize("fetched_email", [None, 12345,])
    def test_is_email_taken_exceptions(self, mocker: MockerFixture, fetched_email):
        """ Test if email is already taken exceptions """
        
        mock_db_session = mocker.Mock()
        mock_db_session.query().filter().first.return_value = None
        
        with pytest.raises(ValueError):
            email_utils.is_email_taken(mock_db_session, fetched_email)
    
    
    @pytest.mark.parametrize("fetched_email", [
        "",
        "email",
        "email@",
        "email@example",
        "email@example.",
        ])
    def test_is_email_valid_exceptions(self, mocker: MockerFixture, fetched_email):
        """ Test validation email format exceptions """
        
        mock_validate_email = mocker.patch("app.utils.email_utils.validate_email")
        mock_validate_email.side_effect = EmailUndeliverableError(f"Invalid email: {fetched_email}")
        
        with pytest.raises(EmailUndeliverableError):
            email_utils.is_email_valid(fetched_email)
        
        mock_validate_email.assert_called_once_with(fetched_email)
        
    
    def test_send_email_success(self, mocker: MockerFixture):
        """ Test success email sending """
        
        mock_db_session = mocker.Mock()
        mock_response = {
            "status": 200,
            "message": "Email sent successfully",
            "validation_code": 123456
        }

        mock_send_email = mocker.patch("app.utils.email_utils.send_email", return_value=mock_response)
        result = email_utils.send_email(mock_db_session, "test@example.com")
        assert result == mock_response
        
        mock_send_email.assert_called_once_with(mock_db_session, "test@example.com")


    def test_send_email_exceptions(self, mocker: MockerFixture):
        """ Test email sending exceptions """
       
        mock_response = {
            "status": 500,
            "message": "SMTP error occurred: Authentication failed"
        }

        mock_send_email = mocker.patch("app.utils.email_utils.send_email", return_value=mock_response)
        result = email_utils.send_email(None, "test@example.com")
        assert result == mock_response
        mock_send_email.assert_called_once_with(None, "test@example.com")
    

    def test_resend_email_success(self, mocker: MockerFixture):
        """ Test re-send email success """
        
        mock_db_session = mocker.Mock()
        code = 123456
        
        mock_user = models.Users(
            id=1,
            username="test",
            full_name="Example Test",
            password="hashed_password",
            email="test@example.com"
            )
        
        mock_email_response = {
            "status": 200, 
            "message": "Email sent successfully", 
            "validation_code": code}
        
        expected_output = {
            "result": code, 
            "user_email": mock_user.email}
        
        mock_db_session.query().filter().first.return_value= mock_user
        mock_send_email = mocker.patch("app.utils.email_utils.send_email", return_value=mock_email_response)
        
        response = email_utils.resend_email(mock_db_session, code)
        
        assert response == expected_output
        
        mock_send_email.assert_called_once_with(mock_db_session, mock_user.email)
    