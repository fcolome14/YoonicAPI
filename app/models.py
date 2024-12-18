from app.database import Base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DOUBLE_PRECISION
from sqlalchemy.sql.expression import null, text
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

class Users(Base):
    """ Users table model """
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    code = Column(Integer, nullable=True)
    code_expiration = Column(TIMESTAMP(timezone=True), nullable=True)
    is_validated = Column(Boolean, nullable=True, default=False)
    # profile_picture = Column(String, nullable=False)
    # follower_count = Column(Integer, nullable=False, default=0)
    # following_count = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    
class TokenTable(Base):
    """ Token table records model """
   
    __tablename__ = "tokentable"
    
    access_token = Column(String, primary_key=True)
    refresh_token = Column(String, nullable=False)
    status = Column(Boolean)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    
    user = relationship("Users", backref="tokentable")
    
class Categories(Base):
    """ Categories table model """
    
    __tablename__ = "cat"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

class Subscriptions(Base):
    """ Subscriptions table model """
    
    __tablename__ = "subs"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    user_id = Column(Integer, primary_key=True, nullable=False) #FK
    event_id = Column(Integer, primary_key=True, nullable=False) #FK
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

class Rates(Base):
    """ Rates table model """
    
    __tablename__ = "rate"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    title = Column(String, nullable=True)
    currency = Column(String, nullable=True, default="EUR")
    amount = Column(DOUBLE_PRECISION, nullable=True, default=0.00)
    line_id = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    
class EventsHeaders(Base):
    
    """" Header of events table model"""
    
    __tablename__ = "events_headers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    address = Column(String, nullable=False)
    coordinates = Column(String, nullable=False)
    img = Column(String, nullable=True)
    img2 = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    category = Column(Integer, ForeignKey("cat.id"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    geom = Column(Geometry("POINT"), nullable=True)
    status = Column(Integer, ForeignKey("status_codes.id"), nullable=False)
    score = Column(Integer, nullable=False, default=0)
    
    user = relationship("Users", backref="events_headers")
    cat = relationship("Categories", backref="events_headers")
    events_lines = relationship("EventsLines", back_populates="header", cascade="all, delete-orphan")
    status_codes = relationship("StatusCodes", backref="events_headers")

class EventsLines(Base):
    
    """" Lines of events table model"""
    
    __tablename__ = "events_lines"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    start = Column(TIMESTAMP(timezone=False), nullable=False)
    end = Column(TIMESTAMP(timezone=False), nullable=False)
    capacity = Column(Integer, nullable=True)
    isPublic = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    header_id = Column(Integer, ForeignKey("events_headers.id", ondelete="CASCADE"), nullable=False)
    
    header = relationship("EventsHeaders", back_populates="events_lines")

class StatusCodes(Base):
    """ Status codes table model """
    
    __tablename__ = "status_codes"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    
class Subcategories(Base):
    """ Subcategory table model """
    
    __tablename__ = "subcat"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    cat = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

class Tags(Base):
    """ Tags table model """
    
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False)
    subcat = Column(Integer, nullable=False)
    weight = Column(Integer, nullable=False, default=1)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
