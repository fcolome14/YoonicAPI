# import pytest
# from fastapi import HTTPException
# from app.routers.users import get_users, create_users
# from fastapi.security.oauth2 import OAuth2PasswordRequestForm
# from app.main import app
# import app.models as models
# import app.utils as utils
    
# class TestUsers:
    
#     @pytest.fixture
#     def mock_db_session(self, mocker):
#         mock_session = mocker.Mock()
        
#         mock_user = models.Users(
#             id=1, 
#             email="test@example.com", 
#             password="hashed_password", 
#             name="Pedro", 
#             lastname="Sanchez", 
#             username="psanchez"
#         )

#         mock_session.query().filter().first.return_value = mock_user
        
#         return mock_session
    
#     @pytest.mark.skipif
#     def test_get_users_succeed(self, mock_db_session):
#         """Test that the user is retrieved successfully."""
        
#         username = "psanchez"
#         expected_json = {
#             "username": username,
#             "email": "test@example.com",
#             "name": "Pedro",
#             "lastname": "Sanchez"
#         }
#         response = get_users(username, mock_db_session)
#         response_json = {
#             "username": response.username,
#             "email": response.email,
#             "name": response.name,
#             "lastname": response.lastname
#         }
        
#         assert response_json == expected_json
    
#     @pytest.mark.skipif 
#     def test_get_users_exception(self, mocker):
#         """Test that the user is retrieved successfully."""
        
#         mock_db_session = mocker.Mock()

#         mock_db_session.query().filter().first.return_value = None
#         username = "piglesias"
#         expected = f"User {username} not found"
        
#         try:
#             get_users(username, mock_db_session)
#         except HTTPException as exc:
#             assert exc.status_code == 404
#             assert exc.detail == expected
