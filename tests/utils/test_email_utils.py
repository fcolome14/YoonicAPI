import pytest
from app.utils import email_utils
from pytest_mock import MockerFixture
import app.models as models
from app.utils import email_utils
import smtplib

class TestEmailUtils:
    
    @pytest.fixture(autouse=True)
    def mock_db_session(self, mocker: MockerFixture):
        return mocker.Mock()
    
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
    
    def test_is_email_taken(self, mocker: MockerFixture, expected_output, fetched_email, mock_db_session):
        """ Test if email is taken for different invalid inputs """
        
        mock_db_session.query().filter().first.return_value = expected_output
        
        response = email_utils.is_email_taken(mock_db_session, fetched_email)
        
        assert response == expected_output
    
    
    @pytest.mark.parametrize("fetched_email", [
        None, 
        12345,
        ])
    
    def test_is_email_taken_exceptions(self, fetched_email, mock_db_session):
        """ Test if email is already taken exceptions """
        
        mock_db_session.query().filter().first.return_value = None
        
        with pytest.raises(ValueError):
            email_utils.is_email_taken(mock_db_session, fetched_email)
    

    def test_send_auth_code_success(self, mocker: MockerFixture, mock_db_session):
        """ Test auth code email sending success """
        
        mock_response = {
            "status": "success",
            "message": 123456
        }

        mock_send_email = mocker.patch("app.utils.email_utils.send_auth_code", return_value=mock_response)
        result = email_utils.send_auth_code(mock_db_session, "test@example.com")
        assert result == mock_response
        
        mock_send_email.assert_called_once_with(mock_db_session, "test@example.com")


    @pytest.mark.parametrize("template, expected_error, side_effect", [
        (0, {"status": "error", "message": "Email verification code template not found"}, FileNotFoundError),
        
        (1, {"status": "error", "message": "SMTP error occurred: "}, smtplib.SMTPException),
        
        (0, {"status": "error", "message": "Failed to connect to the SMTP server"}, ConnectionError),
        
        (0, {"status": "error", "message": "An unexpected error occurred: "}, Exception),
    ])
    
    def test_send_auth_code_exceptions(self, mocker: MockerFixture, mock_db_session, template, expected_error, side_effect):
        """ Test code email sending exceptions """

        mocker.patch("os.getcwd", return_value="../../app/templates")
        
        if side_effect == FileNotFoundError:  # noqa: E721
            mocker.patch("builtins.open", side_effect=FileNotFoundError)
        else:
            mock_template_content = "email_verification_code.html"
            mocker.patch("builtins.open", mocker.mock_open(read_data=mock_template_content))

        mocker.patch("app.utils.email_utils.generate_code", return_value="123456")
        mocker.patch("app.utils.email_utils.create_email_code_token", return_value="test_token")

        mock_smtp = mocker.patch("smtplib.SMTP")
        mock_smtp_instance = mocker.Mock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_instance.starttls.side_effect = side_effect

        result = email_utils.send_auth_code(db=mock_db_session, email="test@example.com", template=template)

        assert result == expected_error
        
        
    def test_resend_auth_code_success(self, mocker: MockerFixture, mock_db_session):
        """ Test success code email re-sending """
        
        mock_user = models.Users(
            id=1, 
            email="test@example.com", 
            password="hashed_password", 
            full_name="Test Example", 
            username="texample",
            code=123456,
            is_validated=True
            )
        mock_response = {
            "status": "success",
            "message": mock_user.code
        }
        expected_output = {"status": "success", "new_code": mock_user.code, "user": mock_user}

        mock_db_session.query().filter().first.return_value = mock_user
        mocker.patch("app.utils.email_utils.send_auth_code", return_value=mock_response)
        
        result = email_utils.resend_auth_code(mock_db_session, mock_user.code)
        
        assert result == expected_output
    
    @pytest.mark.parametrize("mock_user, mock_send_email", [
        (models.Users(
            id=1, 
            email="test@example.com", 
            password="hashed_password", 
            full_name="Test Example", 
            username="texample",
            code=123456,
            is_validated=True
            ), 
         {"status": "error", 
          "message": "SMTP error occurred: "
          }
         ),
        
        (models.Users(
            id=1, 
            email="test@example.com", 
            password="hashed_password", 
            full_name="Test Example", 
            username="texample",
            code=654321,
            is_validated=True
            ), 
         {"status": "error", 
          "message": "SMTP error occurred: "
          }
         ),
        
        ])
    def test_resend_auth_code_errors(self, mocker: MockerFixture, mock_db_session, mock_user, mock_send_email):
        """ Test errors in code email re-sending """

        if not mock_user:
          expected_output = {"status": "error", "message": "Code not found"}  
        expected_output = {"status": "error", "message": mock_send_email.get("message")}

        mock_db_session.query().filter().first.return_value = mock_user
        mocker.patch("app.utils.email_utils.send_auth_code", return_value=mock_send_email)
        
        result = email_utils.resend_auth_code(mock_db_session, mock_user.code)
        
        assert result == expected_output
        