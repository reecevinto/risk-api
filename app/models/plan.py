from sqlalchemy import Boolean, Column, Integer, String, Numeric

from app.db.base import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, unique=True)

    request_limit = Column(Integer)

    # ==============================
    # DAY 6 PHASE 2
    # OVERAGE SETTINGS
    # ==============================

    allow_overage = Column(
        Boolean,
        nullable=False,
        default=False
    )

    overage_price = Column(
    Numeric(10, 4),
    nullable=False,
    default=0
)