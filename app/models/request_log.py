"""
============================================================
REQUEST LOG MODEL
============================================================

Purpose
-------
Stores one completed API request made through the application.

Responsibilities
----------------
✓ Track authenticated user requests
✓ Store submitted risk-analysis inputs
✓ Store risk-analysis results
✓ Track endpoint usage
✓ Track normal vs overage requests
✓ Associate requests with the originating device
✓ Provide the canonical source for usage metering

Architecture
------------
One completed API request produces exactly ONE RequestLog row.

Device fingerprinting does NOT create an additional RequestLog.

Therefore:

    API request
        │
        ├── DeviceFingerprint
        │
        └── RequestLog
                │
                └── device_id → DeviceFingerprint

Billing / metering continues to use RequestLog records.

DeviceFingerprint.request_count is device telemetry only.

IMPORTANT MIGRATION NOTE
------------------------
This model is intentionally aligned with the existing Alembic
migration history.

Current migration HEAD:

    903267aa7fb0
    Add subscription current period start

The existing device_id column is preserved exactly as part of
the Day 8 device-fingerprinting integration.

Do NOT rename, remove, or change existing columns unless a
deliberate schema migration is required.
============================================================
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
)

from sqlalchemy.sql import func

from app.db.base import Base


class RequestLog(Base):
    """
    Persist one completed API request.
    """

    __tablename__ = "request_logs"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # USER
    # ========================================================
    #
    # CRITICAL:
    # Used by usage metering and request ownership.
    # ========================================================

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    # ========================================================
    # REQUEST INPUT DATA
    # ========================================================

    email = Column(
        String,
        nullable=True,
    )

    phone = Column(
        String,
        nullable=True,
    )

    ip = Column(
        String,
        nullable=True,
    )

    # ========================================================
    # ENDPOINT
    # ========================================================
    #
    # Tracks which API endpoint generated the request.
    # ========================================================

    endpoint = Column(
        String,
        nullable=False,
    )

    # ========================================================
    # RISK RESULTS
    # ========================================================

    risk_score = Column(
        Integer,
        nullable=False,
    )

    trust_level = Column(
        String,
        nullable=False,
    )

    # ========================================================
    # RISK FLAGS
    # ========================================================
    #
    # Example:
    #
    # [
    #     "vpn_detected",
    #     "disposable_email"
    # ]
    #
    # ========================================================

    flags = Column(
        JSON,
        nullable=True,
    )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # ========================================================
    # DAY 6 PHASE 2 — OVERAGE TRACKING
    # ========================================================
    #
    # Identifies whether this request was processed as an
    # overage request.
    #
    # ========================================================

    is_overage = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ========================================================
    # DAY 8 PHASE 3 — DEVICE FINGERPRINTING
    # ========================================================
    #
    # Links this request to the DeviceFingerprint record that
    # generated the request.
    #
    # IMPORTANT:
    #
    # This is a foreign-key reference only.
    #
    # It does NOT create another RequestLog.
    #
    # RequestLog remains the canonical billing/metering record.
    #
    # Nullable=True is intentionally preserved so existing
    # historical RequestLog records can remain valid.
    #
    # ========================================================

    device_id = Column(
        Integer,
        ForeignKey("device_fingerprints.id"),
        nullable=True,
    )