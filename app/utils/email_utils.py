import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from string import Template

from app.responses import SystemResponse
from app.schemas.schemas import ResponseStatus
import inspect
from app.utils.fetch_data_utils import (validate_email, 
                                  get_user_data,
                                  get_code_owner)

from app.schemas.schemas import InternalResponse

import pdb

from sqlalchemy import and_
from sqlalchemy.orm import Session

from  app.models import Users
from app.config import settings
from app.oauth2 import create_email_code_token
from app.services.retrieve_service import RetrieveService

from app.services.auth_service import AuthService

VERIFY_CODE_ROUTE = "/auth/verify-code"


def is_email_taken(db: Session, email: str) -> InternalResponse:
    """
    Check if an email is already taken.

    Args:
        db (Session): Database connection.
        email (str): Email.

    Returns:
        InternalResponse: System response indicating whether the email is taken.
    """
    status = ResponseStatus.ERROR
    origin = inspect.stack()[0].function
    
    if not isinstance(email, str) or not email:
        return SystemResponse.internal_response(status, origin, "Email must be provided")
    result = validate_email(db, email)
    if result.status == ResponseStatus.ERROR and result.message == "Not found":
        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, "Email available")
    return result

def send_auth_code(db: Session, email: str, template: int = 0):
    """Send email with an authentication generated code

    Args:
        db (Session): Database connection.
        email (str): Recipient email
        template (int, optional): Used HTML template {0: Account verification, 1: Password recovery}. Defaults to 0.

    Returns:
        Union[dict, int]: Error details as a dictionary or the validation code on success.
    """
    status = ResponseStatus.ERROR
    origin = inspect.stack()[0].function
    
    result: InternalResponse = AuthService.generate_code(db)
    if result.status == ResponseStatus.ERROR:
        return result
    verification_code = result.message
    verification_token = create_email_code_token(
        data={"email": email, "code": verification_code}
    )

    match template:
        case 0:
            email_template_path = os.path.join(
                os.getcwd(), "app", "templates", "email_verification_code.html"
            )
            subject = "Your Verification Code"
        case 1:
            email_template_path = os.path.join(
                os.getcwd(), "app", "templates", "email_recovery.html"
            )
            subject = "Account Recovery Code"
        case _ :
            return SystemResponse.internal_response(
                status, 
                origin,
                "HTML Template not found")
    try:
        with open(email_template_path, "r") as f:
            template_content = f.read()
    except FileNotFoundError:
        return SystemResponse.internal_response(
                status, 
                origin,
                "Email verification code template not found")
        
    verification_url = f"{settings.domain}{VERIFY_CODE_ROUTE}"
    template = Template(template_content)
    html_content = template.substitute(
        verification_token=verification_token,
        verification_url=verification_url,
        verification_code=verification_code,
    )

    response: InternalResponse = send_email(email, subject, html_content)
    if response.status== ResponseStatus.ERROR:
        return response
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, verification_code)

def send_updated_events(db: Session, user_id: int, changes: dict):
    #TODO: REFACTOR JOB
    status = ResponseStatus.ERROR
    origin = inspect.stack()[0].function
    subject = "Updated Activity"
    
    result: InternalResponse = get_user_data(db, user_id)
    if result.status == ResponseStatus.ERROR:
        return SystemResponse.internal_response(result.status, result.origin, result.message)

    email_template_path = os.path.join(
        os.getcwd(), "app", "templates", "event_changed.html"
    )
    try:
        with open(email_template_path, "r") as f:
            template_content = f.read()
    except FileNotFoundError:
        return SystemResponse.internal_response(status, origin, "Updated Event template not found")

    user: Users = result.message
    name = user.full_name[1].split(" ")
    name = name[0] if len(name) > 1 else name
    logo = f"{settings.domain}/static/assets/images/logo_color.png"
    
    event_details = ""
    event_details = RetrieveService.generate_event_changes_html(db, changes, user_id)

    template = Template(template_content)
    html_content = template.substitute(
        user_name=name, event_details=event_details, logo=logo
    )

    result: InternalResponse = send_email(user.email, subject, html_content)
    if result.status == ResponseStatus.ERROR:
        return result
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, "Changes sent via email")

def send_email(email: str, subject: str, html_content: str):
    """
    Send email with a specific HTML content

    Args:
        email (str): Recipient email
        subject (str): Email subject
        html_content (str): Body of the email based on an HTML/CSS file

    Returns:
        _type_: Result of the process
    """
    status = ResponseStatus.ERROR
    origin = inspect.stack()[0].function
    
    msg = MIMEMultipart()
    msg["From"] = settings.email
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.email, settings.email_password)
        server.sendmail(settings.email, email, msg.as_string())
        server.quit()

        return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, "Email sent")

    except smtplib.SMTPException as e:
        return SystemResponse.internal_response(status, origin, f"SMTP error occurred: {str(e)}")
    except ConnectionError:
        return SystemResponse.internal_response(status, origin, "Failed to connect to the SMTP server")
    except Exception as e:
        return SystemResponse.internal_response(status, origin, f"An unexpected error occurred: {str(e)}")

def resend_auth_code(db: Session, code: int):
    origin = inspect.stack()[0].function
    
    result: InternalResponse = get_code_owner(db, code)
    if result.status == ResponseStatus.ERROR:
        return result
    
    user: Users = result.message
    send_result: InternalResponse = send_auth_code(db, user.email)
    if send_result.status == ResponseStatus.ERROR:
        return send_result.status
    return SystemResponse.internal_response(ResponseStatus.SUCCESS, origin, (send_result.message, user))