from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship

from app.db.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    stripe_subscription_id = Column(
        String,
        unique=True,
        nullable=False
    )

    status = Column(
        String,
        nullable=False,
        default="active"
    )

    current_plan = Column(
        String,
        nullable=False
    )

    current_period_end = Column(
        DateTime,
        nullable=True
    )

    user = relationship(
        "User",
        back_populates="subscriptions"
    )