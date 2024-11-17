from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from app.config import settings
# from app.routers import products, users, auth
from fastapi.middleware.cors import CORSMiddleware
from app.routers import users
from app.routers import auth

app = FastAPI()
origins = ["http://www.google.com"]

#Handle CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# app.include_router(products.router)
# app.include_router(users.router)
app.include_router(auth.router)
app.include_router(users.router)
