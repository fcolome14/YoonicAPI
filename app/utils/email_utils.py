from sqlalchemy.orm import Session
import app.models as models
from .utils import generate_code
from app.config import settings
from sqlalchemy import and_
from app.services.retrieve_service import RetrieveService
import smtplib
import os
from string import Template
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.oauth2 import create_email_code_token

VERIFY_CODE_ROUTE = "/auth/verify-code"

def is_email_taken(db: Session, email: str) -> models.Users | None:
    """Check if an email is already taken

    Args:
        db (Session): Database connection
        email (str): Email

    Returns:
        models.Users | None: User using the email
    """
    if not isinstance(email, str) or not email:
        raise ValueError()
    
    return db.query(models.Users).filter(and_(models.Users.email == email, models.Users.is_validated == True)).first()  # noqa: E712


def send_auth_code(db: Session, email: str, template: int = 0):
    """Send email with an authentication generated code

    Args:
        db (Session): Database connection.
        email (str): Recipient email
        template (int, optional): Used HTML template {0: Account verification, 1: Password recovery}. Defaults to 0.

    Returns:
        Union[dict, int]: Error details as a dictionary or the validation code on success.
    """
    verification_code = generate_code(db)
    verification_token = create_email_code_token(data={"email": email, "code": verification_code})
    
    match template:
        case 0:
             email_template_path = os.path.join(os.getcwd(), 'app', 'templates', 'email_verification_code.html')
             subject = 'Your Verification Code'
        case 1:
            email_template_path = os.path.join(os.getcwd(), 'app', 'templates', 'email_recovery.html')
            subject = 'Account Recovery Code'
    try:
        with open(email_template_path, 'r') as f:
            template_content = f.read()
    except FileNotFoundError:
        return {"status": "error", "message": "Email verification code template not found"}
    verification_url = f"{settings.domain}{VERIFY_CODE_ROUTE}"
    template = Template(template_content)
    html_content = template.substitute(verification_token=verification_token, verification_url=verification_url, verification_code=verification_code)
    
    response = send_email(email, subject, html_content)
    if not response or response.get("status") == "error":
        return {"status": "error", "message": response.get("message")}
    
    return {"status": "success", "message": verification_code} 
    
    
def send_updated_events(db: Session, user_id: int, changes: dict):
    user = db.query(models.Users.email, models.Users.full_name, models.Users.username).filter(models.Users.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}
    
    email_template_path = os.path.join(os.getcwd(), 'app', 'templates', 'event_changed.html')
    subject = 'Updated Activity'
    try:
        with open(email_template_path, 'r') as f:
            template_content = f.read()
    except FileNotFoundError:
        return {"status": "error", "message": "Updated Event template not found"}

    name = user[1].split(" ")
    name = name[0] if len(name) > 1 else name
    logo = f'{settings.domain}/static/assets/images/logo_color.png'
    event_details = ""
    event_details = RetrieveService.generate_event_changes_html(db, changes, user_id)

    template = Template(template_content)
    html_content = template.substitute(user_name=name, event_details=event_details, logo=logo)
    
    response = send_email(user[0], subject, html_content)
    if not response or response.get("status") == "error":
        return {"status": "error", "message": response.get("message")}
    
    return {"status": "success", "message": "Event changes sent via email"}

    
    
def send_email(email: str, subject: str, html_content: str):
    """ESend email with a specific HTML content

    Args:
        email (str): Recipient email
        subject (str): Email subject
        html_content (str): Body of the email based on an HTML/CSS file

    Returns:
        _type_: Result of the process
    """
    msg = MIMEMultipart()
    msg['From'] = settings.email
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    try:
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.email, settings.email_password)
        server.sendmail(settings.email, email, msg.as_string())
        server.quit()

        return {"status": "success", "message": "email sent"}

    except smtplib.SMTPException as e:
        return {"status": "error", "message": f"SMTP error occurred: {str(e)}"}
    except ConnectionError:
        return {"status": "error", "message": "Failed to connect to the SMTP server"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
    
def resend_aut_code(db: Session, code: int):
    response = db.query(models.Users).filter(and_(models.Users.code == code)).first()  # noqa: E712

    if response:
        send_result = send_auth_code(db, response.email)
        
        if send_result.get("status") == "success":
            return {"status": "success", "new_code": send_result.get("message"), "user": response}
        else:
            return {"status": "error", "message": send_result.get("message")}
    
    return {"status": "error", "message": "Code not found"}
