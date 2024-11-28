from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from app.config import settings
from app.database.seed import seed_data
from fastapi.middleware.cors import CORSMiddleware
from app.routers import users, auth, posts, legal, recall
import firebase_admin
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.exception_handlers import custom_http_exception_handler
from fastapi.exceptions import HTTPException
from geopy.geocoders import Nominatim
from app.database.connection import get_db

app = FastAPI()
client = Nominatim(user_agent=settings.user_agent)

app.mount("/static", StaticFiles(directory="app/templates"), name="static")
templates = Jinja2Templates(directory="app/templates")

firebase_admin.initialize_app()
print(f"Firebase project '{firebase_admin.get_app().project_id}' initialized")

#CORS handling
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
    seed_data.seed_data(db)

app.add_exception_handler(HTTPException, custom_http_exception_handler)

while True:
    try:
        conn = psycopg2.connect(host=settings.database_hostname, database=settings.database_name, 
                                user=settings.database_username, password=settings.database_password, 
                                cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        print("Connection succesfully stablished with PostgreSQL")
        break
    
    except Exception as error:
        print(f"Error {error}")
        time.sleep(3000)


#Include here all the router scripts
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)
app.include_router(legal.router)
app.include_router(recall.router)
