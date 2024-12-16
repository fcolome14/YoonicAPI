import httpx
from app.config import settings
from haversine import haversine, Unit
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from fastapi import Depends
from math import sin, cos, asin, acos, radians, degrees
from app.database.connection import get_db
import app.models as models
from sqlalchemy import func
from datetime import datetime
import pytz
from app.utils import time_utils

NOMINATIM_BASE_URL = settings.nominatim_base_url
USER_AGENT = settings.user_agent

async def fetch_geocode_data(address: str):
    """
    Fetch geocode data from address to coordinates.
    """
    params = {
        "q": address,
        "format": "json",
        "addressdetails": 1,
    }
    headers = {"User-Agent": USER_AGENT}
    
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(f"{NOMINATIM_BASE_URL}/search", params=params)
        if response.status_code == 200:
            fetched_data = response.json()
            if not fetched_data:
                return {"status": "error", "details": "Site not found"}
            
            lat = fetched_data[0].get("lat")
            lon = fetched_data[0].get("lon")
            address = fetched_data[0].get("display_name")
            return {"status": "success", "point": (float(lat), float(lon)), "address": address}
        
        return {"status": "error", "details": "Error while fetching geocode data"}

async def fetch_reverse_geocode_data(lat: float, lon: float):
    """
    Fetch geocode data from coordinates to address.
    """
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
    }
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(f"{NOMINATIM_BASE_URL}/reverse", params=params)
        if response.status_code == 200:
            fetched_data = response.json()
            if not fetched_data:
                return {"status": "error", "details": "Site not found"}
            if fetched_data.get("error"):
                return {"status": "error", "details": fetched_data.get("error")}
            
            lat = fetched_data.get("lat")
            lon = fetched_data.get("lon")
            address = fetched_data.get("display_name")
            return {"status": "success", "point": (float(lat), float(lon)), "address": address}
        
        return {"status": "error", "details": "Error while fetching geocode data"}
    

def get_bounding_area(point: list[float], radius: int, units: int = 0) -> dict:
    
    lat, lon = point
    earth_radius_km = 6371
    km_to_mile_conv = 0.621371
    
    earth_radius = earth_radius_km
    if units == 1:
        earth_radius = earth_radius * km_to_mile_conv #Conversion to miles
        radius = radius * km_to_mile_conv
    
    lat_r = radians(lat)

    lat_delta = radius / earth_radius
    min_lat = lat - degrees(lat_delta)
    max_lat = lat + degrees(lat_delta)
    
    lon_delta = degrees(asin(sin(lat_delta) / cos(lat_r)))
    min_lon = lon - lon_delta
    max_lon = lon + lon_delta
    
    return {
    "min_lat": min_lat,
    "max_lat": max_lat,
    "min_lon": min_lon,
    "max_lon": max_lon,
    }
    
    
def get_within_events(area: dict, lat: float, lon: float, db: Session = Depends(get_db)):
    
    user_tz = pytz.timezone(time_utils.get_timezone_by_coordinates(lat, lon))
    current_time_utc = datetime.now(pytz.utc)
    current_time_user_tz = current_time_utc.astimezone(user_tz)
    
    bounding_box = func.ST_MakeEnvelope(
        area.get("min_lon"), area.get("min_lat"), area.get("max_lon"), area.get("max_lat"), 4326
    )
    
    headers = db.query(models.EventsHeaders).filter(func.ST_Within(models.EventsHeaders.geom, bounding_box)).all()
    headers_id = [header.id for header in headers]

    if not headers:
        return {"status": "error", "details": "Event not found. Increase the range"}

    lines = db.query(models.EventsLines).filter(
        and_(
            models.EventsLines.header_id.in_(headers_id),
            models.EventsLines.end > current_time_user_tz
        )
    ).all()
    
    if not lines:
        return {"status": "error", "details": "Empty event"}
        
    return {"status": "success", "details": (headers, lines)}

def compute_distance(pointA: tuple, pointB: tuple, units: int = 0) -> float:
    """Compute Haversine distance between two points

    Args:
        pointA (tuple): First point geographical coordinates
        pointB (tuple): Second point geographical coordinates
        units (int, optional): 0: Kilometers | 1: Miles. Defaults to 0 (Km).

    Returns:
        float: Distance in the selected unit
    """
    match(units):
        case 0:
            return round(haversine(pointA, pointB, unit=Unit.KILOMETERS), 3)
        case 1:
            return round(haversine(pointA, pointB, unit=Unit.MILES), 3)


