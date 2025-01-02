from app.models import EventsHeaders

class GenerateStructureService:
    
    @staticmethod
    def generate_header_structure(header: EventsHeaders) -> dict:
        """
        Converts a EventsHeader model to a serializable dict object

        Args:
            header (models.EventsHeaders): Header record fetched from database

        Returns:
            dict: Header record converted to dict
        """
        result = {
            column.name: getattr(header, column.name) 
            for column in header.__table__.columns} if header else None
        result.pop("geom", None)
        return result
