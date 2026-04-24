from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 🔥 Link to user (CRITICAL for usage tracking)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 🔥 Input data
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    ip = Column(String, nullable=True)

    # 🔥 Risk results
    risk_score = Column(Integer, nullable=False)
    trust_level = Column(String, nullable=False)

    # 🔥 Store flags like ["vpn_detected", "disposable_email"]
    flags = Column(JSON, nullable=True)

    # 🔥 Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())