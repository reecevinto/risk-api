from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)

    # API key stored in DB (recommended: later you can hash this)
    key = Column(String, unique=True, index=True, nullable=False)

    # Link to user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Track when key was created (important for auditing)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Optional but VERY useful for real systems
    is_active = Column(Integer, default=1)

    # Relationship back to user (needed for "attach user to request")
    user = relationship("User", back_populates="api_keys")