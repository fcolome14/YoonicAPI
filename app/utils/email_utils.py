from sqlalchemy.orm import Session
import app.models as models
from .utils import generate_code
from app.config import settings
from email_validator import validate_email
from sqlalchemy import and_
import smtplib
import os
from typing import Union
from string import Template
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote_plus

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


def is_email_valid(email: str) -> str:
    """Validate email format

    Args:
        email (str): Email

    Returns:
        str: Email or Exceptions
    """
    return validate_email(email).email

def send_email(db: Session, recipient_email: str, template: int = 0):
    """Send email with a code

    Args:
        db (Session): Database connection.
        recipient_email (str): Email
        template (int, optional): Used HTML template {0: Account verification, 1: Password recovery}. Defaults to 0.

    Returns:
        Union[dict, int]: Error details as a dictionary or the validation code on success.
    """
    
    validation_code = generate_code(db)
    
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
    html_content = template.substitute(verification_code=validation_code, verification_url=verification_url, recipient_email=recipient_email)

    msg = MIMEMultipart()
    msg['From'] = settings.email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.email, settings.email_password)
        server.sendmail(settings.email, recipient_email, msg.as_string())
        server.quit()

        return {"status": "success", "message": validation_code}

    except smtplib.SMTPException as e:
        return {"status": "error", "message": f"SMTP error occurred: {str(e)}"}
    except ConnectionError:
        return {"status": "error", "message": "Failed to connect to the SMTP server"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
    
    
def resend_email(db: Session, code: int):
    
    response = db.query(models.Users).filter(and_(models.Users.code == code)).first()  # noqa: E712

    if response:
        send_result = send_email(db, response.email)
        
        if send_result.get("status") == "success":
            return {"status": "success", "new_code": send_result.get("message"), "user": response}
        else:
            return {"status": "error", "message": send_result.get("message")}
    
    return {"status": "error", "message": "Code not found"}
