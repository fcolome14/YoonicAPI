import httpx
from fastapi import HTTPException
from app.config import settings

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
            
            coordinates = f'{fetched_data[0].get("lat")},{fetched_data[0].get("lon")}'
            address = fetched_data[0].get("display_name")
            return {"status": "success", "point": coordinates, "address": address}
        
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
            
            coordinates = f'{fetched_data.get("lat")},{fetched_data.get("lon")}'
            address = fetched_data.get("display_name")
            return {"status": "success", "point": coordinates, "address": address}
        
        return {"status": "error", "details": "Error while fetching geocode data"}
