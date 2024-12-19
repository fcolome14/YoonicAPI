import pytz
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

import app.models as models
from app.database.connection import get_db
from app.oauth2 import get_user_session
from app.rate_limit import limiter
from app.schemas import schemas
from app.utils import maps_utils

router = APIRouter(prefix="/recall", tags=["Configuration recall"])
utc = pytz.UTC


@router.get(
    "/categories",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
def get_categories(
    db: Session = Depends(get_db),
    _: int = Depends(get_user_session),
    request: Request = None,
) -> schemas.SuccessResponse:
    """Get categories mapping

    Args:
        db (Session, optional): Database session. Defaults to Depends(get_db).
        _ (int, optional): User id. Defaults to Depends(get_user_session).
        request (Request, optional): Header request. Defaults to None.

    Returns:
        schemas.SuccessResponse: Response JSON
    """
    response = db.query(
        models.Categories.id, models.Categories.name, models.Categories.code
    ).all()
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=schemas.ErrorDetails(
                type="GetCategories", message="Not Found", details=None
            ).model_dump(),
        )

    response_dict = [
        {"id": row[0], "category": row[1], "code": row[2]} for row in response
    ]
    return schemas.SuccessResponse(
        message="Categories settings",
        data=response_dict,
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )


@router.get(
    "/tags", status_code=status.HTTP_200_OK, response_model=schemas.SuccessResponse
)
def get_tags(
    category_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_user_session),
    request: Request = None,
) -> schemas.SuccessResponse:
    """Get tags related to a category

    Args:
        category_id (int): _description_
        db (Session, optional): _description_. Defaults to Depends(get_db).
        _ (int, optional): _description_. Defaults to Depends(get_user_session).
        request (Request, optional): _description_. Defaults to None.

    Returns:
        schemas.SuccessResponse: _description_
    """

    response = (
        db.query(
            models.Tags.id,
            models.Tags.name,
            models.Tags.subcat,
            models.Subcategories.code,
            models.Subcategories.name,
        )
        .join(models.Subcategories, models.Subcategories.id == models.Tags.subcat)
        .join(models.Categories, models.Categories.id == models.Subcategories.cat)
        .filter(models.Categories.id == category_id)
        .all()
    )

    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=schemas.ErrorDetails(
                type="GetTags", message="Not Found", details=None
            ).model_dump(),
        )

    result = {}
    for tag_id, tag_name, subcat_id, subcat_code, subcat_name in response:
        subcategory_key = subcat_code

        if subcat_name not in result:
            result[subcat_name] = []

        subcategory_exists = False
        for subcategory in result[subcat_name]:
            if subcategory["subcategory_code"] == subcategory_key:
                subcategory_exists = True
                subcategory["tags"].append({"id": tag_id, "name": tag_name})
                break

        if not subcategory_exists:
            result[subcat_name].append(
                {
                    "subcategory_code": subcategory_key,
                    "tags": [{"id": tag_id, "name": tag_name}],
                }
            )

    final_result = {category_name: result[category_name] for category_name in result}

    return schemas.SuccessResponse(
        message="Tags",
        data=final_result,
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )


@router.get(
    "/address-suggestions",
    status_code=status.HTTP_200_OK,
    response_model=schemas.SuccessResponse,
)
@limiter.limit("10/minute")
async def get_address_suggestions(
    input: str, _: int = Depends(get_user_session), request: Request = None
) -> schemas.SuccessResponse:

    input = input.strip().lower()
    words = input.split(" ")
    contains_number = any(char.isdigit() for char in input)
    if words and len(words) >= 3 and not contains_number:
        fetched_suggestions = await maps_utils.fetch_geocode_data(input, True)
    else:
        fetched_suggestions = []

    if fetched_suggestions.get("status" == "error"):
        fetched_suggestions = []

    return schemas.SuccessResponse(
        message="Adress suggestions",
        data=fetched_suggestions,
        meta={
            "request_id": request.headers.get("request-id", "default_request_id"),
            "client": request.headers.get("client-type", "unknown"),
        },
    )
