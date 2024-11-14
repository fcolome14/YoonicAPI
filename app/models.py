from app.database import Base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.sql.expression import null, text
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.orm import relationship

class Product(Base):
    
    """" Product table model"""
    
    __tablename__ = "product"
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    id_sale = Column(Boolean, server_default='False')
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    
    user = relationship("Users") #Its referencing the "Users" class sqlalchemy

class Users(Base):
    
    """ User table model """
    
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    phone_number = Column(String, nullable=True)