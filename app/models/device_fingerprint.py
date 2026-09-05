"""
============================================================
DEVICE FINGERPRINT MODEL
============================================================

Day 8 — Phase 3
Device Fingerprinting System

Purpose
-------
This model stores a permanent identity for every browser/device
that communicates with the Risk Intelligence API.

Unlike RequestLog, which records every individual request,
DeviceFingerprint represents the long-term identity of the device.

Relationship

User
    ├── Device A
    │      ├── Request 1
    │      ├── Request 2
    │      └── Request 3
    │
    ├── Device B
    │      ├── Request 4
    │      └── Request 5
    │
    └── Device C
           └── Request 6

This allows the platform to answer questions such as:

• Is this a new device?
• Is this a trusted device?
• Has this device been seen before?
• How many requests has this device made?
• Has this device switched users?
• Has this device changed browsers?
• Has this device changed operating systems?

The actual browser fingerprint is NEVER stored directly.

Instead, we store a SHA-256 fingerprint hash.

This follows the same privacy-conscious approach used by
commercial fraud-detection systems.
============================================================
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
)

from sqlalchemy.sql import func

from app.db.base import Base


class DeviceFingerprint(Base):
    """
    Permanent device identity.

    One row represents one browser/device.

    Request logs link to this model through device_id.
    """

    __tablename__ = "device_fingerprints"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # USER OWNER
    # ========================================================

    # Device belongs to one user.
    #
    # Future versions may allow shared-device intelligence
    # across accounts for fraud detection.

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # ========================================================
    # DEVICE IDENTITY
    # ========================================================

    # SHA-256 fingerprint hash.
    #
    # Example:
    #
    # 3d77b0fe9c5...
    #
    # Raw fingerprint characteristics are not stored as the
    # device identity itself.

    device_hash = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    # ========================================================
    # DEVICE INFORMATION
    # ========================================================

    # Browser name
    #
    # Chrome
    # Firefox
    # Edge
    # Safari

    browser = Column(
        String,
        nullable=True,
    )

    # Browser version
    #
    # Example:
    #
    # 138.0.7204

    browser_version = Column(
        String,
        nullable=True,
    )

    # Operating system
    #
    # Windows
    # Linux
    # macOS
    # Android
    # iOS

    os = Column(
        String,
        nullable=True,
    )

    # Operating system version

    os_version = Column(
        String,
        nullable=True,
    )

    # Platform classification
    #
    # Desktop
    # Mobile
    # Tablet

    platform = Column(
        String,
        nullable=True,
    )

    # Device language
    #
    # en-US
    # en-GB

    language = Column(
        String,
        nullable=True,
    )

    # Browser timezone
    #
    # Africa/Nairobi

    timezone = Column(
        String,
        nullable=True,
    )

    # Screen resolution
    #
    # Example:
    #
    # 1920x1080

    screen_resolution = Column(
        String,
        nullable=True,
    )

    # ========================================================
    # DEVICE ACTIVITY
    # ========================================================

    # First time this device appeared.

    first_seen = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Last time this device was used.

    last_seen = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Number of API requests performed using this device.
    #
    # IMPORTANT:
    # This is DEVICE TELEMETRY.
    #
    # It is NOT the billing/metering counter.
    #
    # RequestLog remains the canonical source for usage
    # metering and billing.

    request_count = Column(
        Integer,
        default=0,
        nullable=False,
    )

    # ========================================================
    # DEVICE TRUST
    # ========================================================

    # Has this device been verified and considered trusted?

    is_trusted = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Has this device been blocked?
    #
    # Future phases may automatically block abusive or
    # high-risk devices.

    is_blocked = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ========================================================
    # AUDIT
    # ========================================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )