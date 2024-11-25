from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.config import settings


router = APIRouter(prefix="/legal", tags=['Terms and conditions'])
templates = Jinja2Templates(directory="app/templates")

@router.get("/terms-of-service/")
def terms_of_service(request: Request = None):
    return templates.TemplateResponse("terms_of_service.html", {"request": request, "url": settings.domain, "email": settings.email})

@router.get("/privacy-policy/")
def privacy_policy(request: Request = None):
    return templates.TemplateResponse("privacy_policy.html", {"request": request, "url": settings.domain, "email": settings.email})

@router.get("/cookies-policy/")
def cookies_policy(request: Request = None):
    return templates.TemplateResponse("cookies_policy.html", {"request": request, "url": settings.domain, "email": settings.email})