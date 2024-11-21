from app.database import Base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.sql.expression import null, text
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.orm import relationship

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
    
    user = relationship("Users", backref="tokens")
    
class Categories(Base):
    """ Categories table model """
    
    __tablename__ = "cat"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    code = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

class Categories(Base):
    """ Subscriptions table model """
    
    __tablename__ = "subs"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    user_id = Column(Integer, primary_key=True, nullable=False) #FK
    event_id = Column(Integer, primary_key=True, nullable=False) #FK
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    
class Events(Base):
    
    """" Events table model"""
    
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    id_sale = Column(Boolean, server_default='False')
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    #user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    
    #user = relationship("Users") #Its referencing the "Users" class sqlalchemy
