from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, index=True, nullable=False)

    name = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔥 Day 3 addition: link to API keys
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")