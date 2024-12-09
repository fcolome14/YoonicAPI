from sqlalchemy.orm import Session
from typing import List
import app.models as models
from app.utils import maps_utils

class RetrieveService:
    @staticmethod
    def generate_nearby_events_structure(db: Session, headers: List[models.EventsHeaders], lines: List[models.EventsLines], reference_point: List[float], unit: int = 0):
        event_data = []
        
        for header in headers:
            event_lines = [line for line in lines if line.header_id == header.id]
            try:
                lat, lon = header.coordinates.split(",")
                event_coordinates = float(lat), float(lon)
            except ValueError:
                event_coordinates = (0.0, 0.0)
                
            event_dict = {
                "id": header.id,
                "title": header.title,
                "description": header.description,
                "address": header.address,
                "coordinates": header.coordinates,
                "img": header.img,
                "img2": header.img2,
                "owner_id": header.owner_id,
                "category": header.category,
                "distance": maps_utils.compute_distance(reference_point, event_coordinates, unit),
                "distance_unit": "km" if unit == 0 else "miles",
                "schedule": []
            }
            
            for line in event_lines:
                line_dict = {
                    "start": line.start.strftime("%Y-%m-%d %H:%M:%S"),
                    "end": line.end.strftime("%Y-%m-%d %H:%M:%S"),
                    "capacity": line.capacity,
                    "isPublic": line.isPublic,
                }
                
                rates = db.query(models.Rates).filter(models.Rates.line_id == line.id).all()
                rate_details = []
                for rate in rates:
                    rate_dict = {
                        "title": rate.title,
                        "currency": rate.currency,
                        "amount": rate.amount,
                    }
                    rate_details.append(rate_dict)
                
                line_dict["rates"] = rate_details
                event_dict["schedule"].append(line_dict)
            
            event_data.append(event_dict)

        return event_data
