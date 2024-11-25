from fastapi import HTTPException, APIRouter
from app.utils import maps_utils as maps

router = APIRouter(prefix="/posts", tags=['Posts'])

@router.get("/geocode/")
async def geocode(address: str):
    """
    Geocoding: Get coordinates (latitude, longitude) for a given address.
    """
    return await maps.fetch_geocode_data(address)

@router.get("/reverse/")
async def reverse_geocode(lat: float, lon: float):
    """
    Reverse Geocoding: Get an address for a given latitude and longitude.
    """
    return await maps.fetch_reverse_geocode_data(lat, lon)
