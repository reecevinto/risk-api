from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String, unique=True, index=True, nullable=False)

    name = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Current billing plan
    plan_id = Column(Integer, ForeignKey("plans.id"))

    # Stripe customer mapping
    stripe_customer_id = Column(
        String,
        unique=True,
        nullable=True
    )

    # Relationships
    api_keys = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    plan = relationship(
        "Plan"
    )

    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan"
    )