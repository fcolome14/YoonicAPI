from datetime import datetime
from typing import List, Union

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models import EventsHeaders, EventsLines, Rates
from app.schemas import DeletePostInput, NewPostInput, RateDetails
from app.schemas.bases import UpdateChanges
from app.services.rate_service import RateService, pack_rates
from app.services.repeater_service import (select_repeater_custom_mode,
                                           select_repeater_single_mode)
from app.utils import maps_utils, time_utils, utils

class EventUpdateService:

    @staticmethod
    async def _update_header(
        db: Session, user_id: int, table: int, changes: UpdateChanges = None
    ):
        """
        Update header row
        """
        if not changes:
            return {"status": "error", "details": "No changes to apply in header"}
        if table != 0:
            return {"status": "error", "details": "Invalid table specified for header"}

        row, updates = [item.id for item in changes], [item.update for item in changes]
        fetched_record = (
            db.query(EventsHeaders)
            .filter(and_(EventsHeaders.owner_id == user_id, EventsHeaders.id == row[0]))
            .first()
        )

        if not fetched_record:
            return {"status": "error", "details": "Record not found in header"}

        tracked_changes = []
        for update in updates[0]:
            field = update.field
            new_value = update.value
            old_value = getattr(fetched_record, field, None)

            if await EventUpdateService._handle_coordinates_update(
                tracked_changes, row[0], fetched_record, field, old_value, new_value
            ):
                continue  # Skip if coordinates were updated
            if await EventUpdateService._handle_address_update(
                tracked_changes, row[0], fetched_record, field, old_value, new_value
            ):
                continue  # Skip if address was updated
            if old_value != new_value:
                EventUpdateService._update_record(
                    fetched_record,
                    field,
                    new_value,
                    tracked_changes,
                    row[0],
                    field,
                    old_value,
                    "header",
                )

        db.commit()
        return (
            {"status": "success", "details": tracked_changes}
            if len(tracked_changes) > 0
            else {"status": "error", "details": "No changes applied in header"}
        )

    @staticmethod
    async def _handle_coordinates_update(
        tracked_changes, row_id, fetched_record, field, old_value, new_value
    ):
        if field == "coordinates":
            if not EventUpdateService._is_valid_coordinates(new_value):
                EventUpdateService.append_tracked_change(
                    tracked_changes,
                    "error",
                    "Invalid coordinates type. Expected <[float, float]>",
                    row_id,
                    fetched_record.id,
                    field,
                    old_value,
                    new_value,
                    "header",
                )
                return True

            if f"{new_value[0]},{new_value[1]}" == old_value:
                EventUpdateService.append_tracked_change(
                    tracked_changes,
                    "error",
                    "Unchanged location",
                    row_id,
                    fetched_record.id,
                    field,
                    old_value,
                    new_value,
                    "header",
                )
                return True

            result = await maps_utils.fetch_reverse_geocode_data(
                new_value[0], new_value[1]
            )
            if result.get("status") == "error":
                EventUpdateService.append_tracked_change(
                    tracked_changes,
                    "error",
                    result.get("details"),
                    row_id,
                    fetched_record.id,
                    field,
                    old_value,
                    new_value,
                    "header",
                )
                return True

            point = result.get("point")
            setattr(fetched_record, "address", result.get("address"))
            setattr(fetched_record, "coordinates", f"{point[0]},{point[1]}")
            setattr(
                fetched_record,
                "geom",
                func.ST_SetSRID(func.ST_Point(point[1], point[0]), 4326),
            )
            EventUpdateService.append_tracked_change(
                tracked_changes,
                "success",
                None,
                row_id,
                fetched_record.id,
                field,
                old_value,
                new_value,
                "header",
            )
            return True
        return False

    @staticmethod
    async def _handle_address_update(
        tracked_changes, row_id, fetched_record, field, old_value, new_value
    ):
        if field == "address":
            if not isinstance(new_value, str):
                EventUpdateService.append_tracked_change(
                    tracked_changes,
                    "error",
                    "Invalid address type. Expected <str>",
                    row_id,
                    fetched_record.id,
                    field,
                    old_value,
                    new_value,
                    "header",
                )
                return True

            if new_value == old_value:
                EventUpdateService.append_tracked_change(
                    tracked_changes,
                    "error",
                    "Unchanged location",
                    row_id,
                    fetched_record.id,
                    field,
                    old_value,
                    new_value,
                    "header",
                )
                return True

            result = await maps_utils.fetch_geocode_data(new_value)
            if result.get("status") == "error":
                EventUpdateService.append_tracked_change(
                    tracked_changes,
                    "error",
                    result.get("details"),
                    row_id,
                    fetched_record.id,
                    field,
                    old_value,
                    new_value,
                    "header",
                )
                return True

            point = result.get("point")
            setattr(fetched_record, "address", result.get("address"))
            setattr(fetched_record, "coordinates", f"{point[0]},{point[1]}")
            setattr(
                fetched_record,
                "geom",
                func.ST_SetSRID(func.ST_Point(point[1], point[0]), 4326),
            )
            EventUpdateService.append_tracked_change(
                tracked_changes,
                "success",
                None,
                row_id,
                fetched_record.id,
                field,
                old_value,
                new_value,
                "header",
            )
            return True
        return False

    @staticmethod
    def _is_valid_coordinates(coordinates):
        return (
            isinstance(coordinates, tuple)
            and len(coordinates) == 2
            and isinstance(coordinates[0], (float, int))
            and isinstance(coordinates[1], (float, int))
        )

    @staticmethod
    def _update_record(
        fetched_record,
        field,
        new_value,
        tracked_changes,
        row_id,
        field_name,
        old_value,
        origin,
    ):
        setattr(fetched_record, field, new_value)
        EventUpdateService.append_tracked_change(
            tracked_changes,
            "success",
            None,
            row_id,
            fetched_record.id,
            field_name,
            old_value,
            new_value,
            origin,
        )

    @staticmethod
    async def _update_lines(
        db: Session, user_id: int, table: int, changes: UpdateChanges = None
    ):
        """
        Update lines rows
        """
        if not changes:
            return {"status": "error", "details": "No changes to apply in lines"}

        if table != 1:
            return {"status": "error", "details": "Invalid table specified for lines"}

        row_ids = [item.id for item in changes]
        updates = [
            {
                "id": item.id,
                "updates": [
                    {"field": update.field, "value": update.value}
                    for update in item.update
                ],
            }
            for item in changes
        ]

        fetched_header = (
            db.query(EventsHeaders)
            .join(EventsLines, EventsLines.header_id == EventsHeaders.id)
            .filter(EventsLines.id.in_(row_ids), EventsHeaders.owner_id == user_id)
            .first()
        )

        if not fetched_header:
            return {"status": "error", "details": "Unauthorized user"}

        fetched_records = (
            db.query(EventsLines)
            .filter(
                and_(
                    EventsLines.header_id == fetched_header.id,
                    EventsLines.id.in_(row_ids),
                )
            )
            .all()
        )
        if not fetched_records:
            return {"status": "error", "details": "Records not found"}

        tracked_changes = []

        for item in fetched_records:
            record_update = next((u for u in updates if u["id"] == item.id), None)

            if not record_update:
                continue

            for update in record_update["updates"]:
                field = update["field"]
                new_value = update["value"]
                old_value = getattr(item, field, None)

                if isinstance(old_value, datetime) and time_utils.is_valid_datetime(
                    new_value
                ):
                    new_value = datetime.strptime(new_value, "%Y-%m-%d %H:%M:%S.%f")

                    if field == "start" and new_value > item.end:
                        EventUpdateService.append_tracked_change(
                            tracked_changes,
                            "error",
                            f"Starting date must be before {item.end}",
                            item.id,
                            fetched_header.id,
                            field,
                            old_value,
                            new_value,
                            "lines",
                        )
                        continue  # Skip item

                    if field == "end" and new_value < item.start:
                        EventUpdateService.append_tracked_change(
                            tracked_changes,
                            "error",
                            f"Ending date must be after {item.start}",
                            item.id,
                            fetched_header.id,
                            field,
                            old_value,
                            new_value,
                            "lines",
                        )
                        continue  # Skip item

                if old_value != new_value:
                    EventUpdateService.append_tracked_change(
                        tracked_changes,
                        "success",
                        None,
                        item.id,
                        fetched_header.id,
                        field,
                        old_value,
                        new_value,
                        "lines",
                    )
                    setattr(item, field, new_value)

        db.commit()

        return (
            {"status": "success", "details": tracked_changes}
            if len(tracked_changes) > 0
            else {"status": "error", "details": "No changes applied in lines"}
        )

    @staticmethod
    async def _update_rates(
        db: Session, user_id: int, table: int, changes: UpdateChanges = None
    ):
        """
        Update rates rows
        """
        if not changes:
            return {"status": "error", "details": "No changes to apply in rates"}

        if table != 2:
            return {"status": "error", "details": "Invalid table specified for rates"}

        row_ids = [item.id for item in changes]
        updates = [
            {
                "id": item.id,
                "updates": [
                    {"field": update.field, "value": update.value}
                    for update in item.update
                ],
            }
            for item in changes
        ]

        fetched_ids = (
            db.query(EventsHeaders.id, EventsLines.id)
            .join(EventsLines, EventsLines.header_id == EventsHeaders.id)
            .join(Rates, Rates.line_id == EventsLines.id)
            .filter(Rates.id.in_(row_ids), EventsHeaders.owner_id == user_id)
            .all()
        )

        if not fetched_ids:
            return {"status": "error", "details": "Unauthorized user for rates"}

        header_ids, lines_id = [item[0] for item in fetched_ids], [
            item[1] for item in fetched_ids
        ]
        header_ids, lines_id = list(set(header_ids)), set(lines_id)
        header_ids = header_ids[0] if len(header_ids) == 1 else header_ids

        fetched_records = (
            db.query(Rates)
            .filter(and_(Rates.line_id.in_(lines_id), Rates.id.in_(row_ids)))
            .all()
        )
        if not fetched_records:
            return {"status": "error", "details": "Records not found in rates"}

        tracked_changes = []

        for item in fetched_records:
            record_update = next((u for u in updates if u["id"] == item.id), None)

            if not record_update:
                continue

            for update in record_update["updates"]:
                field = update["field"]
                new_value = update["value"]
                old_value = getattr(item, field, None)

                if old_value != new_value:
                    EventUpdateService.append_tracked_change(
                        tracked_changes,
                        "success",
                        None,
                        item.id,
                        header_ids,
                        field,
                        old_value,
                        new_value,
                        "rate",
                    )
                    setattr(item, field, new_value)

        db.commit()

        return (
            {"status": "success", "details": tracked_changes}
            if len(tracked_changes) > 0
            else {"status": "error", "details": "No changes applied in rates"}
        )

    @staticmethod
    def append_tracked_change(
        tracked_changes,
        status,
        message,
        record_id,
        header_id,
        field,
        old_value,
        new_value,
        origin,
    ):
        """
        Helper function to append a tracked change to the list.
        """
        tracked_changes.append(
            {
                "status": status,
                "origin": origin,
                "message": message,
                "header_id": header_id,
                "record_id": record_id,
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
            }
        )

    @staticmethod
    def group_changes_by_event(changes):
        relevant_changes = []
        for item in changes.get("details", []):
            if item.get("status") != "error":
                for change in item.get("details", []):
                    header_id = change.get("header_id")
                    origin = change.get("origin")
                    field = change.get("field")
                    old_value = change.get("old_value")
                    new_value = change.get("new_value")
                    record_id = change.get("record_id")

                    header_entry = next(
                        (entry for entry in relevant_changes if header_id in entry),
                        None,
                    )
                    if not header_entry:
                        header_entry = {header_id: {"header": [], "lines": {}}}
                        relevant_changes.append(header_entry)

                    header_data = header_entry[header_id]

                    if origin == "header":
                        header_data["header"].append(
                            {
                                "field": field,
                                "old_value": old_value,
                                "new_value": new_value,
                            }
                        )
                    elif origin == "lines":
                        if record_id not in header_data["lines"]:
                            header_data["lines"][record_id] = {
                                "fields": [],
                                "rates": [],
                            }
                        header_data["lines"][record_id]["fields"].append(
                            {
                                "field": field,
                                "old_value": old_value,
                                "new_value": new_value,
                            }
                        )
                    elif origin == "rate":
                        if record_id not in header_data["lines"]:
                            header_data["lines"][record_id] = {
                                "fields": [],
                                "rates": [],
                            }
                        header_data["lines"][record_id]["rates"].append(
                            {
                                "rate_id": record_id,
                                "field": field,
                                "old_value": old_value,
                                "new_value": new_value,
                            }
                        )
        return relevant_changes


class EventDeleteService:
    @staticmethod
    def delete_events(db: Session, delete_input: DeletePostInput, user_id: int):
        delete_ids = [item.id for item in delete_input.deletes]
        if delete_input.table == 0:
            fetched_records = (
                db.query(EventsHeaders)
                .filter(
                    and_(
                        EventsHeaders.id.in_(delete_ids),
                        EventsHeaders.owner_id == user_id,
                    )
                )
                .all()
            )
            if not fetched_records:
                return {"status": "error", "details": "Header record not found"}
            for header in fetched_records:
                db.delete(header)
            db.commit()
            return {
                "status": "success",
                "details": (
                    f"Headers {delete_ids} deleted"
                    if len(delete_ids) > 1
                    else f"Header {delete_ids} deleted"
                ),
            }

        elif delete_input.table == 1:
            fetched_records_with_header = (
                db.query(EventsLines, EventsHeaders)
                .join(EventsHeaders)
                .filter(
                    EventsLines.id.in_(delete_ids), EventsHeaders.owner_id == user_id
                )
                .all()
            )

            if not fetched_records_with_header:
                return {"status": "error", "details": "Lines record not found"}

            lines_to_delete = [
                line for line, _ in fetched_records_with_header
            ]  # (HEADER, LINE)
            for line in lines_to_delete:
                db.delete(line)
            db.commit()
            return {
                "status": "success",
                "details": (
                    f"Lines {delete_ids} deleted"
                    if len(delete_ids) > 1
                    else f"Line {delete_ids} deleted"
                ),
            }

        fetched_records_with_header = (
            db.query(Rates, EventsLines, EventsHeaders)
            .join(EventsLines, EventsLines.header_id == EventsHeaders.id)
            .join(Rates, Rates.line_id == EventsLines.id)
            .filter(Rates.id.in_(delete_ids), EventsHeaders.owner_id == user_id)
            .all()
        )

        if not fetched_records_with_header:
            return {"status": "error", "details": "Rates records not found"}

        lines_to_delete = [
            rate for rate, _, _ in fetched_records_with_header
        ]  # (RATES, LINE, HEADER)
        for line in lines_to_delete:
            db.delete(line)
        db.commit()
        return {
            "status": "success",
            "details": (
                f"Rates {delete_ids} deleted"
                if len(delete_ids) > 1
                else f"Rate {delete_ids} deleted"
            ),
        }
