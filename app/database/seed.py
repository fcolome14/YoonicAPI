""" Load static data to database """
from sqlalchemy.orm import Session
import app.models as models

class Seed:
    @staticmethod
    def seed_data(db: Session):
        
        if db.query(models.Categories).count() == 0:
            
            add_categories = [
            models.Categories(code="cat.1", name="Sports"),
            models.Categories(code="cat.2", name="Culture"), 
            models.Categories(code="cat.3", name="Gastronomy"),
            models.Categories(code="cat.4", name="Social"),   
            ]
            
            db.add_all(add_categories)
            db.commit()
            for category in add_categories:
                db.refresh(category)

seed_data = Seed()