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
    def generate_header_structure(header: models.EventsHeaders):
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
            "status": header.status,
        }

        return event_dict

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
    def generate_event_changes_html(db: Session, changes: dict, user_id: int):
        html_content = """
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 20px;
                }
                h3 {
                    color: #2c3e50;
                    margin-bottom: 5px;
                }
                h4 {
                    color: #16a085;
                    margin-bottom: 5px;
                }
                h5 {
                    color: #2980b9;
                    margin-bottom: 5px;
                }
                ul {
                    margin-left: 20px;
                    list-style-type: circle;
                }
                li {
                    margin-bottom: 5px;
                    padding: 10px;
                    border-radius: 4px;
                }
                .line-item:nth-child(even) {
                    background-color: #f7f7f7; /* Lighter grey for even lines */
                }
                .line-item:nth-child(odd) {
                    background-color: #e9ecef; /* Slightly darker grey for odd lines */
                }
                .change {
                    color: #e74c3c;
                }
                .highlight {
                    background-color: #f9f9f9;
                    padding: 5px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            </style>
        </head>
        <body>
        """

        for change_group in changes:
            if isinstance(change_group, dict):
                for header_id, data in change_group.items():
                    # Add Header Data
                    header_data = (
                        db.query(models.EventsHeaders)
                        .filter(
                            and_(
                                models.EventsHeaders.owner_id == user_id,
                                models.EventsHeaders.id == header_id,
                            )
                        )
                        .first()
                    )
                    html_content += f"<h3 style='color: #2a9d8f; margin-bottom: 0.5em;'>{header_data.title.upper()}</h3>"
                    html_content += f"<h4 style='color: #264653; margin-bottom: 1em;'>📍 {header_data.address}</h4>"

                    if data.get("header"):
                        html_content += "<h4 style='color: #e76f51;'>What's new:</h4><ul style='list-style-type: none; padding-left: 1em;'>"
                        for _, header_change in enumerate(data["header"]):
                            field = header_change.get("field")
                            old_value = header_change.get("old_value")
                            new_value = header_change.get("new_value")
                            if field == "address":
                                emoji = "📍"
                            elif field == "title":
                                emoji = "📝"
                            else:
                                emoji = "🔄"
                            html_content += f"<li class='line-item' style='margin-bottom: 0.5em;'>{emoji} <strong style='color: #f4a261;'>{field.capitalize()}:</strong> '<span style='color: #e63946;'>{old_value}</span>' &rarr; '<span style='color: #2a9d8f;'>{new_value}</span>'</li>"
                        html_content += "</ul>"

                    # Add Lines Data
                    if data.get("lines"):
                        for record_id, line_data in data["lines"].items():
                            lines_data = (
                                db.query(models.EventsLines)
                                .filter(
                                    and_(
                                        models.EventsLines.header_id == header_id,
                                        models.EventsLines.id == record_id,
                                    )
                                )
                                .first()
                            )
                            if not lines_data:
                                break
                            formatted_start = lines_data.start.strftime(
                                "%B %d (%I:%M %p)"
                            )
                            formatted_end = lines_data.end.strftime("%B %d (%I:%M %p)")
                            html_content += f"<h4 style='color: #2a9d8f; margin-top: 1em;'>📅 {formatted_start} - {formatted_end}</h4>"

                            if line_data.get("fields"):
                                html_content += "<h5 style='color: #e76f51;'>Scheduling changes:</h5><ul style='list-style-type: none; padding-left: 1em;'>"
                                for idx, field_change in enumerate(line_data["fields"]):
                                    field = field_change.get("field")
                                    old_value = field_change.get("old_value")
                                    new_value = field_change.get("new_value")
                                    if field == "start" or field == "end":
                                        emoji = "📅"
                                        old_value = field_change.get(
                                            "old_value"
                                        ).strftime("%B %d (%I:%M %p)")
                                        new_value = field_change.get(
                                            "new_value"
                                        ).strftime("%B %d (%I:%M %p)")
                                    else:
                                        emoji = "🔄"
                                    html_content += f"<li class='line-item' style='margin-bottom: 0.5em;'> {emoji} <strong style='color: #f4a261;'>{field.capitalize()}:</strong> '<span style='color: #e63946;'>{old_value}</span>' &rarr; '<span style='color: #2a9d8f;'>{new_value}</span>'</li>"
                                html_content += "</ul>"

                            # Add Rates Data
                            new_rate_id = -1
                            if line_data.get("rates"):
                                html_content += "<h5 style='color: #e76f51;'>💸 What's new for rates:</h5><ul style='list-style-type: none; padding-left: 1em;'>"
                                for rate_change in line_data["rates"]:
                                    rate_id = rate_change.get("rate_id")
                                    field = rate_change.get("field")
                                    if rate_id != new_rate_id:
                                        rate_data = (
                                            db.query(models.Rates)
                                            .filter(models.Rates.id == rate_id)
                                            .first()
                                        )
                                        new_rate_id = rate_id
                                        old_value = f"<strong style='color: #f4a261;'>{rate_data.title.capitalize()}:</strong> '<span style='color: #2a9d8f;'>{rate_change.get('old_value')} {rate_data.currency}</span>'"
                                        new_value = f"<strong style='color: #f4a261;'>{rate_data.title.capitalize()}:</strong> '<span style='color: #2a9d8f;'>{rate_change.get('new_value')} {rate_data.currency}</span>'"
                                        html_content += f"<li class='line-item' style='margin-bottom: 0.5em;'>💰 '<span style='color: #e63946;'>{old_value}</span>' &rarr; '<span style='color: #2a9d8f;'>{new_value}</span>'</li>"
                                html_content += "</ul>"

        html_content += """
        </body>
        </html>
        """
        return html_content

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
