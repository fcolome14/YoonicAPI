from sqlalchemy.orm import Session
from app.models import Users
from app.utils import utils, time_utils, fetch_data_utils

from app.responses import SystemResponse, InternalResponse
from app.schemas.schemas import ResponseStatus, RegisterInput
import inspect

class UserService:
    
    @staticmethod
    def validate_password_recovery(db: Session, username: str, new_password: str):
        origin = inspect.stack()[0].function
        status = ResponseStatus.ERROR
        
        result: InternalResponse = fetch_data_utils.validate_username(db, username)
        if result.status == ResponseStatus.ERROR:
            return result
            
        user: Users = result.message
        result = utils.is_password_valid(new_password, user.password)
        if result.status == ResponseStatus.SUCCESS:
            message = "New password must be different from old one"
            return SystemResponse.internal_response(status, origin, message)

        result = utils.is_password_strong(new_password)
        if result.status == ResponseStatus.ERROR:
            return result
        
        result = utils.hash_password(new_password)
        if result.status == ResponseStatus.ERROR:
            return result
        user.password = result.message
        
        result = fetch_data_utils.update_db(db, user)
        if result.status == ResponseStatus.ERROR:
            return result
        
        return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, origin, "Password changed successfully")
        