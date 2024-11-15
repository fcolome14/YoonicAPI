import pytest
from fastapi import HTTPException
from app.routers.users import get_users, create_users
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from app.main import app
import app.models as models
import app.utils as utils

class TestUsers:
    
    @pytest.fixture
    def mock_db_session(self, mocker):
        mock_session = mocker.Mock()
        
        mock_user = models.Users(
            id=1, 
            email="test@example.com", 
            password="hashed_password", 
            name="Pedro", 
            lastname="Sanchez", 
            username="psanchez"
        )

        # Simulate returning a user when queried
        mock_session.query().filter().first.return_value = mock_user
        
        return mock_session
    
    def test_get_users_succeed(self, mock_db_session):
        """Test that the user is retrieved successfully."""
        
        username = "psanchez"
        expected_json = {
            "username": username,
            "email": "test@example.com",
            "name": "Pedro",
            "lastname": "Sanchez"
        }
        
        # Ensure the function returns the correct user data
        response = get_users(username, mock_db_session)
        response_json = {
            "username": response.username,
            "email": response.email,
            "name": response.name,
            "lastname": response.lastname
        }
        
        assert response_json == expected_json
    
    def test_get_users_exception(self, mock_db_session):
        """Test that an HTTPException is raised when the user is not found."""
        
        # Mock no user found
        mock_db_session.query().filter().first.return_value = None
        username = "piglesias"
        expected = f"User {username} not found"
        
        # Use pytest.raises to expect the exception
        with pytest.raises(HTTPException) as exc:
            get_users(username, mock_db_session)
        
        # Check the exception details
        assert exc.value.status_code == 404
        assert exc.value.detail == expected