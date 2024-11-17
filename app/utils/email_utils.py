from sqlalchemy.orm import Session
from fastapi import HTTPException
import app.models as models
from .utils import generate_code
from app.config import settings
from email_validator import validate_email
from sqlalchemy import or_, and_
import smtplib
import os
from typing import Union
from string import Template
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote_plus

def is_email_taken(db: Session, email: str) -> models.Users | None:
    """Check if an email is already taken

    Args:
        db (Session): Database connection
        email (str): Email

    Returns:
        models.Users | None: User using the email
    """
    return db.query(models.Users).filter(and_(models.Users.email == email, models.Users.is_validated == True)).first()  # noqa: E712

def is_email_valid(email: str) -> str:
    """Validate email format

    Args:
        email (str): Email

    Returns:
        str: Email or Exceptions
    """
    return validate_email(email).email

def send_validation_email(db: Session, recipient_email: str) -> Union[dict, int]:
    """Send email to verify a user account.

    Args:
        db (Session): Database connection.
        recipient_email (str): Email.

    Returns:
        dict | int: Error details as a dictionary or the validation code on success.
    """
    validation_code = generate_code(db)
    email_template_path = os.path.join(os.getcwd(), 'app', 'templates', 'email_template.html')

    try:
        with open(email_template_path, 'r') as f:
            template_content = f.read()
    except FileNotFoundError:
        return {"status": 404, "message": "Email verification code template not found"}

    verification_url = f"{settings.domain}/auth/verify/{quote_plus(validation_code)}"
    template = Template(template_content)
    html_content = template.substitute(verification_code=validation_code, verification_url=verification_url)

    msg = MIMEMultipart()
    msg['From'] = settings.email
    msg['To'] = recipient_email
    msg['Subject'] = 'Your Verification Code'
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.email, settings.email_password)
        server.sendmail(settings.email, recipient_email, msg.as_string())
        server.quit()

        return {"status": 200, "message": "Email sent successfully", "validation_code": validation_code}

    except smtplib.SMTPException as e:
        return {"status": 500, "message": f"SMTP error occurred: {str(e)}"}
    except ConnectionError:
        return {"status": 503, "message": "Failed to connect to the SMTP server"}
    except Exception as e:
        return {"status": 500, "message": f"An unexpected error occurred: {str(e)}"}

def send_recovery_email(db: Session, recipient_email: str) -> Union[dict, int]:
    """Send email to recover a user password.

    Args:
        db (Session): Database connection.
        recipient_email (str): Email.

    Returns:
        dict | int: Error details as a dictionary or the validation code on success.
    """
    validation_code = generate_code(db)
    email_template_path = os.path.join(os.getcwd(), 'app', 'templates', 'email_recovery.html')

    try:
        with open(email_template_path, 'r') as f:
            template_content = f.read()
    except FileNotFoundError:
        return {"status": 404, "message": "Email recovery template not found"}

    verification_url = f"{settings.domain}/auth/password_recovery/{quote_plus(validation_code)}"
    template = Template(template_content)
    html_content = template.substitute(verification_code=validation_code, verification_url=verification_url)

    msg = MIMEMultipart()
    msg['From'] = settings.email
    msg['To'] = recipient_email
    msg['Subject'] = 'Account password recovery'
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        server.starttls()
        server.login(settings.email, settings.email_password)
        server.sendmail(settings.email, recipient_email, msg.as_string())
        server.quit()

        return {"status": 200, "message": "Email sent successfully", "validation_code": validation_code}

    except smtplib.SMTPException as e:
        return {"status": 500, "message": f"SMTP error occurred: {str(e)}"}
    except ConnectionError:
        return {"status": 503, "message": "Failed to connect to the SMTP server"}
    except Exception as e:
        return {"status": 500, "message": f"An unexpected error occurred: {str(e)}"}

def resend_email(db: Session, code: int):
    response = db.query(models.Users).filter(and_(models.Users.code == code, models.Users.is_validated == False)).first()  # noqa: E712

    if response:
        send_result = send_validation_email(db, response.email)
        
        if send_result["status"] == 200:
            return {"result": send_result["validation_code"], "user_email": response.email}
        else:
            return {"error": send_result["message"], "status": send_result["status"]}
    
    return {"error": "Record not found", "status": 404}
