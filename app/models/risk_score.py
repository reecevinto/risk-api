from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db.base import Base

class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String)
    phone = Column(String)
    ip = Column(String)
    score = Column(Integer)
    risk_level = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)