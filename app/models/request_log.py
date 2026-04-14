from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base

class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String)
    email = Column(String)
    phone = Column(String)
    risk_score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)