from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from app.models import EventsHeaders, EventsLines, Rates
from app.utils.fetch_data_utils import get_header
from app.services.post_service import SourceTable
from app.utils.time_utils import convert_string_to_utc


class HTMLTemplates:
    @staticmethod
    def generate_event_changes_html(db: Session, changes: dict, user_id: int) -> str:
        def fetch_header_data(header_id):
            return (
                db.query(EventsHeaders)
                .filter(and_(EventsHeaders.owner_id == user_id, EventsHeaders.id == header_id))
                .first()
            )

        def fetch_line_data(header_id, record_id):
            return (
                db.query(EventsLines)
                .filter(and_(EventsLines.header_id == header_id, EventsLines.id == record_id))
                .first()
            )

        def fetch_rate_data(rate_id):
            return db.query(Rates).filter(Rates.id == rate_id).first()

        def format_header_changes(header_changes):
            html = "<h4 style='color: #e76f51;'>Event Details Updated:</h4><ul>"
            for change in header_changes:
                field, old_value, new_value = change["field"], str(change["old_value"]), str(change["new_value"])
                emoji = "📍" if field == "address" else "📝" if field == "title" else "🔄"

                if field == "title":
                    text = f"Title has changed to '{new_value}'."
                    emoji = "🚩"
                elif field == "address":
                    text = f"New location: {new_value}."
                    emoji = "📍"
                else:
                    continue

                html += f"<li>{emoji} {text}</li>"
            return html + "</ul>"

        def format_line_changes(record_id, line_data):
            html = ""
            line = fetch_line_data(header_id, record_id)
            if not line:
                return html

            formatted_start_day = line.start.strftime("%B %d")
            formatted_end_day = line.end.strftime("%B %d")
            formatted_start_time = line.start.strftime("%I:%M %p")
            formatted_end_time = line.end.strftime("%I:%M %p")
            date_line = (
                f"{formatted_start_day} ({formatted_start_time})"
                if formatted_start_day == formatted_end_day
                else f"{formatted_start_day} ({formatted_start_time}) to {formatted_end_day} ({formatted_end_time})"
            )

            html += f"<div class='day-block'><h4 class='highlighted-date'>{date_line}</h4>"

            if line_data["fields"]:
                html += "<h5 style='color: #e76f51;'>Relevant Updates:</h5><ul>"
                for field_change in line_data["fields"]:
                    field, old_value, new_value = field_change["field"], field_change["old_value"], field_change["new_value"]
                    emoji = "📅" if field in ["start", "end"] else "🔄"
                    
                    if isinstance(new_value, str) and (field == "start" or field == "end"):
                        new_value = datetime.strptime(new_value, "%Y-%m-%d %H:%M:%S.%f")
                    
                    if field == "capacity":
                        emoji = "🔺👥" if int(new_value) > int(old_value) else "🔻👥"
                        text = f"Maximum {new_value} attendees."
                    elif field == "isPublic":
                        emoji = "🔓" if new_value == "True" else "⛔"
                        text = "Now is public." if new_value == "True" else "Now is private."
                    elif field == "start":
                        formatted_new_start_day = new_value.strftime("%B %d")
                        formatted_new_start_time = new_value.strftime("%I:%M %p")
                        text = f"Now it starts in {formatted_new_start_day} at {formatted_new_start_time}."
                    elif field == "end":
                        formatted_new_end_day = new_value.strftime("%B %d")
                        formatted_new_end_time = new_value.strftime("%I:%M %p")
                        text = f"Now it ends in {formatted_new_end_day} at {formatted_new_end_time}."

                    html += f"<li>{emoji} {text}</li>"
                html += "</ul>"

            return html

        def format_rate_changes(rate_changes):
            html = "<h5 style='color: #e76f51;'>💸 Rate Updates:</h5><ul>"
            for rate_change in rate_changes:
                rate = fetch_rate_data(rate_change["rate_id"])
                if rate:
                    field = rate_change["field"]
                    old_value = str(rate_change["old_value"])
                    new_value = str(rate_change["new_value"])
                    emoji = "💱"

                    if field == "title":
                        continue
                    elif field == "amount":
                        if float(new_value) > float(old_value):
                            emoji = "🔺💲"
                        if float(new_value) < float(old_value):
                            emoji = "🔻💲"
                        text = f"Now '{rate.title}': <strong>{new_value} {rate.currency}</strong>."
                        if float(new_value) == 0.00:
                            emoji = "🤑"
                            text = f"'{rate.title}' is now <strong>free!</strong>"
                    elif field == "currency":
                        text = f"Now '{rate.title}' is in {new_value}."

                    html += f"<li>{emoji} {text}</li>"
            return html + "</ul>"

        html_content = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 20px; }
                h3, h4, h5 { margin-bottom: 0.5em; color: #264653; }
                ul { list-style-type: none; padding-left: 1em; }
                li { margin-bottom: 0.5em; }
                .day-block { padding: 15px; margin-bottom: 20px; border-radius: 8px; }
                .day-block:nth-child(even) { background-color: #f7f7f7; }
                .day-block:nth-child(odd) { background-color: #e9ecef; }
                .highlighted-date { 
                    background-color: #3c3c3c; /* Light grey background */
                    color: #f0f0f0; /* Darker text for contrast */
                    font-weight: bold; 
                    font-size: 18px;
                    padding: 10px; 
                    border-radius: 5px; 
                    text-align: center; /* Center-align text */
                    margin-bottom: 10px; /* Space below the date block */
                }
            </style>
        </head>
        <body>
        """

        for change_group in changes:
            for header_id, data in change_group.items():
                header = fetch_header_data(header_id)
                if header:
                    html_content += f"<h3>{header.title.upper()}</h3><h4>📍 {header.address}</h4>"
                    if data[SourceTable.HEADER.value]:
                        html_content += format_header_changes(data[SourceTable.HEADER.value])
                    if data[SourceTable.LINES.value]:
                        for record_id, line_data in data[SourceTable.LINES.value].items():
                            html_content += format_line_changes(record_id, line_data)
                            if line_data[SourceTable.RATES.value]:
                                html_content += format_rate_changes(line_data[SourceTable.RATES.value])

        html_content += "</body></html>"
        return html_content


