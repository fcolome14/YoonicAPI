import time

import firebase_admin
import psycopg2
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from geopy.geocoders import Nominatim
from psycopg2.extras import RealDictCursor
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database.connection import get_db
from app.database.seed import Seed
from app.exception_handlers import custom_http_exception_handler
from app.rate_limit import limiter, rate_limit_handler
from app.routers import auth, legal, posts, recall, users

app = FastAPI()
client = Nominatim(user_agent=settings.user_agent)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.mount("/static", StaticFiles(directory="app/templates"), name="static")
templates = Jinja2Templates(directory="app/templates")

firebase_admin.initialize_app()
print(f"Firebase project '{firebase_admin.get_app().project_id}' initialized")

# CORS handling
origins = ["http://www.google.com", settings.domain]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def seed_database():
    db = next(get_db())
    Seed.seed_data(db)


app.add_exception_handler(HTTPException, custom_http_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

while True:
    try:
        conn = psycopg2.connect(
            host=settings.database_hostname,
            database=settings.database_name,
            user=settings.database_username,
            password=settings.database_password,
            cursor_factory=RealDictCursor,
        )
        cursor = conn.cursor()
        print("Connection succesfully stablished with PostgreSQL")
        break

    except Exception as error:
        print(f"Error {error}")
        time.sleep(3000)


# Include here all the router scripts
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(legal.router)
app.include_router(recall.router)
