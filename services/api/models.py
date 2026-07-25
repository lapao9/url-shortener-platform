from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

class URL(Base):
    __tablename__ = "urls"
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(10), unique=True, index=True, nullable=False)
    original_url = Column(String(2048), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ClickEvent(Base):
    __tablename__ = "click_events"
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(10), index=True, nullable=False)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now())
    user_agent = Column(String(512))
    ip_address = Column(String(45))