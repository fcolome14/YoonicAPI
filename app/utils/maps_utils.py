import httpx
from fastapi import HTTPException
from app.config import settings

NOMINATIM_BASE_URL = settings.nominatim_base_url
USER_AGENT = settings.user_agent

async def fetch_geocode_data(address: str):
    """
    Fetch geocode data (latitude and longitude) for a given address.
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
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Error fetching geocode data")

async def fetch_reverse_geocode_data(lat: float, lon: float):
    """
    Fetch reverse geocode data (address) for a given latitude and longitude.
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
            return response.json()
        raise HTTPException(status_code=response.status_code, detail="Error fetching reverse geocode data")
