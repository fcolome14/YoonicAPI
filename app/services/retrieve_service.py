from datetime import datetime
from typing import List

from sqlalchemy import and_
from sqlalchemy.orm import Session

import app.models as models
from app.utils import maps_utils


class RetrieveService:
    @staticmethod
    def generate_nearby_events_structure(
        db: Session,
        headers: List[models.EventsHeaders],
        lines: List[models.EventsLines],
        reference_point: List[float],
        unit: int = 0,
    ):
        event_data = []

        for header in headers:
            if lines:
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
                "distance": maps_utils.compute_distance(
                    reference_point, event_coordinates, unit
                ),
                "distance_unit": "km" if unit == 0 else "miles",
                "schedule": [],
            }

            if not lines:
                event_data.append(event_dict)
                continue

            for line in event_lines:
                line_dict = {
                    "id": line.id,
                    "start": line.start.strftime("%Y-%m-%d %H:%M:%S"),
                    "end": line.end.strftime("%Y-%m-%d %H:%M:%S"),
                    "capacity": line.capacity,
                    "isPublic": line.isPublic,
                }

                rates = (
                    db.query(models.Rates).filter(models.Rates.line_id == line.id).all()
                )
                rate_details = []
                for rate in rates:
                    rate_dict = {
                        "id": rate.id,
                        "title": rate.title,
                        "currency": rate.currency,
                        "amount": rate.amount,
                    }
                    rate_details.append(rate_dict)

                line_dict["rates"] = rate_details
                event_dict["schedule"].append(line_dict)

            event_data.append(event_dict)

        return event_data

    @staticmethod
    def generate_updated_events_structure(
        db: Session,
        headers: List[models.EventsHeaders],
        lines: List[models.EventsLines],
    ):
        event_data = []

        for header in headers:
            event_lines = [line for line in lines if line.header_id == header.id]
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
                "schedule": [],
            }

            for line in event_lines:
                line_dict = {
                    "id": line.id,
                    "start": line.start.strftime("%Y-%m-%d %H:%M:%S"),
                    "end": line.end.strftime("%Y-%m-%d %H:%M:%S"),
                    "capacity": line.capacity,
                    "isPublic": line.isPublic,
                }

                rates = (
                    db.query(models.Rates).filter(models.Rates.line_id == line.id).all()
                )
                rate_details = []
                for rate in rates:
                    rate_dict = {
                        "id": rate.id,
                        "title": rate.title,
                        "currency": rate.currency,
                        "amount": rate.amount,
                    }
                    rate_details.append(rate_dict)

                line_dict["rates"] = rate_details
                event_dict["schedule"].append(line_dict)

            event_data.append(event_dict)

        return event_data

    @staticmethod
    def generate_details_events_structure(
        db: Session,
        selected_header_id: models.EventsHeaders,
        lat: float,
        lon: float,
        radius: float,
        user_id: int,
        unit: int = 0,
    ):
        selected_event_header = (
            db.query(models.EventsHeaders)
            .filter(
                and_(
                    models.EventsHeaders.id == selected_header_id,
                    models.EventsHeaders.owner_id == user_id,
                )
            )
            .first()
        )
        if not selected_event_header:
            return {
                "status": "error",
                "details": "Event not found or user not authorized",
            }
        selected_event_lines = (
            db.query(models.EventsLines)
            .filter(and_(models.EventsLines.header_id == selected_header_id))
            .all()
        )

        events_within_area, reference_point = RetrieveService.get_events_within_area(
            db, lat, lon, radius, unit
        )
        current_event = RetrieveService.generate_nearby_events_structure(
            db, [selected_event_header], selected_event_lines, reference_point, unit
        )
        if events_within_area.get("status") == "error":
            related_events = []
        else:
            nearby_header, _ = events_within_area.get("details")
            nearby_related_headers = [
                header
                for header in nearby_header
                if header.category == selected_event_header.category
                and header.id != selected_header_id
            ]
            related_events = RetrieveService.generate_nearby_events_structure(
                db, nearby_related_headers, [], reference_point, unit
            )

        return current_event, related_events

    @staticmethod
    # type: ignore
    def get_events_within_area(db: Session, lat: float, lon: float, radius: int = 10, unit: int = 0) -> (dict, List[float]):
        reference_point = [lat, lon]
        area = maps_utils.get_bounding_area(
            point=reference_point, radius=radius, units=unit
        )
        return (
            maps_utils.get_within_events(area, db=db, lat=lat, lon=lon),
            reference_point,
        )
