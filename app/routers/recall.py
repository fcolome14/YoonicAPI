from fastapi import HTTPException, APIRouter, status, Depends, Request
from sqlalchemy.orm import Session
from app.database.connection import get_db
import pytz
from app.schemas import schemas
from app.oauth2 import get_user_session
from app.utils import time_utils, utils, maps_utils
import app.models as models

router = APIRouter(prefix="/recall", tags=["Configuration recall"])
utc = pytz.UTC

@router.get("/categories", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse)
def get_categories(db: Session = Depends(get_db), _: int = Depends(get_user_session), request: Request = None) -> schemas.SuccessResponse:
    """Get categories mapping

    Args:
        db (Session, optional): Database session. Defaults to Depends(get_db).
        _ (int, optional): User id. Defaults to Depends(get_user_session).
        request (Request, optional): Header request. Defaults to None.

    Returns:
        schemas.SuccessResponse: Response JSON
    """
    response = db.query(models.Categories.id, models.Categories.name, models.Categories.code).all()
    
    response_dict = [{"id": row[0], "category": row[1], "code": row[2]} for row in response]
    return schemas.SuccessResponse(
        message="Categories settings",
        data=response_dict,
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        }
    )