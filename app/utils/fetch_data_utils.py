from app.responses import SystemResponse
from app.schemas.schemas import ResponseStatus
from app.schemas.schemas import InternalResponse
import inspect
from typing import Union, List
from sqlalchemy.orm import Session
from app.models import Users, EventsHeaders, EventsLines, Rates, Categories, Tags, Subcategories
from app.services.common.structures import GenerateStructureService
from sqlalchemy import and_, or_
from app.utils.time_utils import is_date_expired, compute_expiration_time
from app.utils.utils import hash_password, is_password_valid

def validate_email(db: Session, email: str) -> InternalResponse:
    """
    Validate if email is available (account already exists in the database)

    Args:
        db (Session): DB Session
        email (str): Provided email

    Returns:
        InternalResponse: Internal response
    """
    status = ResponseStatus.SUCCESS
    origin = inspect.stack()[0].function
    
    try:
        user = db.query(Users).filter(and_(Users.email == email, Users.is_validated == True)).first() # noqa: E712
        if not user:
            status = ResponseStatus.ERROR
            message = "Not found"
        else:
            message = user
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

def validate_username(db: Session, username: str) -> InternalResponse:
    """
    Get a registered username
    
    Args:
        db (Session): DB Session
        username (str): Provided username

    Returns:
        InternalResponse: Internal response
    """

    status = ResponseStatus.SUCCESS
    origin = inspect.stack()[0].function
    
    try:
        user = (
            db.query(Users)
            .filter(and_(
                Users.username == username, 
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

def validate_account(db: Session, username: str, password: str) -> InternalResponse:

    status = ResponseStatus.SUCCESS
    origin = inspect.stack()[0].function
    
    try:
        user = (
            db.query(
                Users)
            .filter(and_(
                Users.username == username,
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

def account_is_available(
    db: Session, 
    email: str, 
    username: str) -> InternalResponse:

    status = ResponseStatus.SUCCESS
    origin = inspect.stack()[0].function
    
    try:
        user = (
            db.query(
                Users)
            .filter(or_(
                Users.username == username,
                Users.email == email)).
            first())
        
        if not user:
            message = "Not found"
        else:
            status = ResponseStatus.ERROR
            message = user
    except Exception as exc:
        status = ResponseStatus.ERROR
        message = f"Database error raised: {exc}"
    
    return SystemResponse.internal_response(status, origin, message)

def validate_code(db: Session, code: int, email: str) -> InternalResponse:
    """Check if a code has not expired yet and still exists

    Args:
        db (Session): Connection Session
        code (int): Code to check
        email (str): Email

    Returns:
        InternalResponse: Internal response
    """
    status = ResponseStatus.ERROR
    origin = inspect.stack()[0].function
    
    fetched_record = (
        db.query(Users)
        .filter(and_(Users.code == code, 
                     Users.email == email))
        .first()
    )

    if not fetched_record or not fetched_record.code_expiration:
        return SystemResponse.internal_response(status, origin, "Code not found")
    result: InternalResponse = is_date_expired(fetched_record.code_expiration)
    if result.status == ResponseStatus.ERROR:
        return result
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, 
                                            origin, 
                                            fetched_record)

def refresh_code(db: Session, 
                 code: int, 
                 email: str, 
                 username: str,
                 isRecovery: bool = False) -> InternalResponse:
    
    status = ResponseStatus.ERROR
    origin = inspect.stack()[0].function
    
    user = (
        db.query(Users)
        .filter(and_(Users.username == username, 
                     Users.email == email))
        .first()
    )
    
    if not user:
            return SystemResponse.internal_response(status, origin, "User not found")
    if not isRecovery:
        if not user.code_expiration:
            return SystemResponse.internal_response(status, origin, "Code not found")
    
    result = compute_expiration_time()
    if result.status == ResponseStatus.ERROR:
        return result
    user.code = code
    user.code_expiration = result.message
    
    result = update_db(db, user)
    if result.status == ResponseStatus.ERROR:
        return result
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, 
                                            origin, 
                                            user)
    
def add_user(db: Session, user: Users):
    origin = inspect.stack()[0].function
    
    user.is_validated = True
    user.code = None
    user.code_expiration = None
    
    result: InternalResponse = update_db(db, user)
    if result.status == ResponseStatus.ERROR:
        return result
    return SystemResponse.internal_response(
        ResponseStatus.SUCCESS, 
        origin, 
        result.message)

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

def add_post(
    db: Session,
    user_id: int,
    header_id: int, 
    lines: any) -> InternalResponse:
    origin = inspect.stack()[0].function
    
    result: InternalResponse = approve_header_status(db, user_id, header_id)
    if result.status == ResponseStatus.ERROR:
        return result
    lines_result: InternalResponse = build_lines(header_id, lines)
    if lines_result.status == ResponseStatus.ERROR:
        return lines_result
    result = commit_db(db, lines_result.message[0], True)
    if result.status == ResponseStatus.ERROR:
        return result
    result = build_rates(lines_result.message)
    if result.status == ResponseStatus.ERROR:
        return result
    result = commit_db(db, result.message, True)
    if result.status == ResponseStatus.ERROR:
        return result
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, result.message)

def commit_db(
    db: Session, 
    data: any, 
    multiple: bool = False) -> InternalResponse:
    origin = inspect.stack()[0].function
    
    if multiple:
        db.add_all(data)
        db.commit()
        for line in data:
            db.refresh(line)
    else:
        db.add(data)
        db.commit()
        db.refresh(data)
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, data)

def update_db(
    db: Session, 
    data: any) -> InternalResponse:
    origin = inspect.stack()[0].function
    
    db.commit()
    db.refresh(data)
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, data)

def build_rates(
    result_lines: tuple
    ) -> InternalResponse:
    origin = inspect.stack()[0].function
    
    lines, rates = result_lines

    if not isinstance(lines, list):
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Expected dict for lines"
            )
    if not isinstance(rates, list):
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Expected list for rates"
            ) 
    if len(lines) != len(rates):
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Invalid rates-lines structure"
            )
        
    rates_list = []
    for key, values in enumerate(rates):
        line_id = lines[key].id
        if isinstance(values, list):
            for value in values:
                if not isinstance(value, list):
                    rates_list.append(
                        Rates(
                        title=value["title"],
                        amount=value["amount"],
                        currency=value["currency"],
                        line_id=line_id)
                        )
                else:
                    for rate in value:
                        rates_list.append(
                    Rates(
                        title=rate["title"],
                        amount=rate["amount"],
                        currency=rate["currency"],
                        line_id=line_id)
                        )
        else:
            rates_list.append(
                Rates(
                title=values["title"],
                amount=values["amount"],
                currency=values["currency"],
                line_id=line_id)
                )
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, rates_list)

def build_lines(
    header_id: int,
    lines: dict
    ) -> InternalResponse:
    origin = inspect.stack()[0].function
    
    if isinstance(lines, dict):
        lines_models, line_rates = [], []
        for _, value in lines.items():
            if isinstance(value, list):
                for line in value:
                    lines_models.append(
                        EventsLines(
                            header_id=header_id,
                            start=line["start"],
                            end=line["end"],
                            capacity=line["capacity"],
                            isPublic=line["isPublic"])
                    )
                    line_rates.append(line["rates"])
            else:
                lines_models.append(
                        EventsLines(
                            header_id=header_id,
                            start=value["start"],
                            end=value["end"],
                            capacity=value["capacity"],
                            isPublic=value["isPublic"])
                    )
                line_rates.append(value["rates"])
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, (lines_models, line_rates))

def approve_header_status(db: Session, 
    user_id: int, 
    header_id: int
    ) -> InternalResponse:
    
    origin = inspect.stack()[0].function
    fetched_header = (
    db.query(EventsHeaders)
    .filter(
        and_(
            EventsHeaders.owner_id == user_id,
            EventsHeaders.id == header_id,
        )
    )
    .first()
    )

    if not fetched_header:
        return SystemResponse.internal_response(ResponseStatus.ERROR, origin, "Header not found")
    if fetched_header.status == 3:
        return SystemResponse.internal_response(ResponseStatus.ERROR, origin, "Post already approved")
    
    fetched_header.status = 3
    result: InternalResponse = commit_db(db, fetched_header)
    if result.status == ResponseStatus.ERROR:
        return result
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, result.message)

def get_categories(
    db: Session, 
    ) -> InternalResponse:
    origin = inspect.stack()[0].function
    
    categories = db.query(
        Categories.id, 
        Categories.name, 
        Categories.code
        ).all()
    
    if not categories:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Not found")
    
    response = [
        {"id": row[0], "category": row[1], "code": row[2]} for row in categories
    ]
    return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            response)

def get_tags(
    db: Session,
    category_id: int, 
    ) -> InternalResponse:
    origin = inspect.stack()[0].function
    
    fetched_data = (
        db.query(
            Tags.id,
            Tags.name,
            Tags.subcat,
            Subcategories.code,
            Subcategories.name,
        )
        .join(Subcategories, Subcategories.id == Tags.subcat)
        .join(Categories, Categories.id == Subcategories.cat)
        .filter(Categories.id == category_id)
        .all()
    )
    
    if not fetched_data:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Not found")
        
    result = build_tags(fetched_data)
    if result.status == ResponseStatus.ERROR:
        return result
    
    tags = result.message
    return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            tags)

def build_tags(
    tags: list,
    ) -> InternalResponse:
    
    origin = inspect.stack()[0].function
    result = {}
    for tag_id, tag_name, subcat_id, subcat_code, subcat_name in tags:
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
    return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            final_result)

def get_header(
    db: Session, 
    user_id: int,
    header_id: Union[int, List[int]],
    ) -> InternalResponse:
    
    origin = inspect.stack()[0].function
    
    if isinstance(header_id, int):
        header = (
                db.query(EventsHeaders)
                .filter(and_(EventsHeaders.owner_id == user_id, 
                            EventsHeaders.id == header_id))
                .first()
            )
    elif isinstance(header_id, list) and all(isinstance(d, int) for d in header_id):
        header = (
                db.query(EventsHeaders)
                .filter(and_(EventsHeaders.owner_id == user_id, 
                            EventsHeaders.id.in_(header_id)))
                .all()
            )
    else:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Invalid type")
    if not header:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Not found")
    return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            header)

def get_header_from_lines(
    db: Session, 
    user_id: int,
    lines_ids: list,
    ) -> InternalResponse:
    
    origin = inspect.stack()[0].function
    
    header = (
            db.query(EventsHeaders)
            .join(EventsLines, EventsLines.header_id == EventsHeaders.id)
            .filter(EventsLines.id.in_(lines_ids), EventsHeaders.owner_id == user_id)
            .first()
        )
    
    if not header:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Not found")
    return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            header)

def get_selected_rates_from_same_lines(
    db: Session, 
    rates_ids: int,
    lines_ids: list,
    ) -> InternalResponse:
    
    origin = inspect.stack()[0].function
    
    rates = (
            db.query(Rates)
            .filter(and_(Rates.line_id.in_(lines_ids), Rates.id.in_(rates_ids)))
            .all()
        )
    
    if not rates:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Not found")
    return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            rates)

def get_header_and_lines_from_rates(
    db: Session, 
    user_id: int,
    rates_ids: list,
    ) -> InternalResponse:
    
    origin = inspect.stack()[0].function
    
    header_and_lines_ids = (
            db.query(EventsHeaders.id, EventsLines.id)
            .join(EventsLines, EventsLines.header_id == EventsHeaders.id)
            .join(Rates, Rates.line_id == EventsLines.id)
            .filter(Rates.id.in_(rates_ids), EventsHeaders.owner_id == user_id)
            .all()
        )
    
    if not header_and_lines_ids:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Not found")
    return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            header_and_lines_ids)

def get_selected_lines_from_same_header(
    db: Session, 
    header_id: int,
    lines_ids: list,
    ) -> InternalResponse:
    
    origin = inspect.stack()[0].function
    
    lines = (
            db.query(EventsLines)
            .filter(
                and_(
                    EventsLines.header_id == header_id,
                    EventsLines.id.in_(lines_ids),
                )
            )
            .all()
        )
    
    if not lines:
        return SystemResponse.internal_response(
            ResponseStatus.ERROR, 
            origin, 
            "Not found")
    return SystemResponse.internal_response(
            ResponseStatus.SUCCESS, 
            origin, 
            lines)
