from app.responses import SystemResponse
from app.schemas.schemas import ResponseStatus
from app.schemas.schemas import InternalResponse
import inspect
from sqlalchemy.orm import Session
from  app.models import Users, EventsHeaders
from app.services.common.structures import GenerateStructureService
from sqlalchemy import and_

def validate_email(db: Session, email: str) -> InternalResponse:
    """
    Validate if email is available

    Args:
        db (Session): DB Session
        email (str): Provided email

    Returns:
        InternalResponse: Internal response
    """
    status = ResponseStatus.SUCCESS
    origin = inspect.stack()[0].function
    
    try:
        result = db.query(Users).filter(and_(Users.email == email, Users.is_validated == True)).first() # noqa: E712
        if not result:
            status = ResponseStatus.ERROR
            message = "Not found"
        else:
            message = result
    except Exception as exc:
        status = ResponseStatus.ERROR
        message = f"Database error raised: {exc}"
    
    return SystemResponse.internal_response(status, origin, message)

def get_user_data(db: Session, user_id: int) -> InternalResponse:
    """
    Get a registered user
    
    Args:
        db (Session): DB Session
        user_id (int): User id

    Returns:
        InternalResponse: Internal response
    """

    status = ResponseStatus.SUCCESS
    origin = inspect.stack()[0].function
    
    try:
        user = (
            db.query(
                Users.email, 
                Users.full_name, 
                Users.username)
            .filter(and_(
                Users.id == user_id, 
                Users.is_validated == True)).  # noqa: E712
            first())
        
        if not user:
            status = ResponseStatus.ERROR
            message = "Not found"
        else:
            message = user
    except Exception as exc:
        status = ResponseStatus.ERROR
        message = f"Database error raised: {exc}"
    
    return SystemResponse.internal_response(status, origin, message)

def get_code_owner(db: Session, code: int) -> InternalResponse:
    """
    Get owner (user) of a code

    Args:
        db (Session): DB Session
        code (int): Provided code

    Returns:
        InternalResponse: Internal response
    """

    status = ResponseStatus.SUCCESS
    origin = inspect.stack()[0].function
    
    try:
        user = (
            db.query(
                Users.email, 
                Users.full_name, 
                Users.username)
            .filter(Users.code == code).  # noqa: E712
            first())
        
        if not user:
            status = ResponseStatus.ERROR
            message = "Not found"
        else:
            message = user
    except Exception as exc:
        status = ResponseStatus.ERROR
        message = f"Database error raised: {exc}"
    
    return SystemResponse.internal_response(status, origin, message)

def pending_headers(db: Session, user_id: int) -> InternalResponse:
    origin = inspect.stack()[0].function
    
    fetched_header = (
    db.query(EventsHeaders)
    .filter(
        and_(
            EventsHeaders.status == 1,
            EventsHeaders.owner_id == user_id,
        )
    )
    .first()
    )

    if not fetched_header:
        return SystemResponse.internal_response(ResponseStatus.ERROR, origin, "Record not found")
    data = GenerateStructureService.generate_header_structure(fetched_header)
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, data)