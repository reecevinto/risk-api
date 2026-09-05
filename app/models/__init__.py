"""
============================================================
SQLAlchemy MODEL PACKAGE
============================================================

Central export point for all SQLAlchemy models.

IMPORTANT
---------
The actual SQLAlchemy metadata registration is handled by:

    app.db.base

This module provides convenient model imports for application
code and ensures all SQLAlchemy models are available through
the app.models package.

All models listed here must correspond to actual model modules
under:

    app/models/

DEVICE FINGERPRINTING — DAY 8 PHASE 3
--------------------------------------
DeviceFingerprint is part of the active device-intelligence
architecture.

The current device architecture is:

    DeviceFingerprint
            │
            │ id
            ▼
       RequestLog
            │
            ├── user_id
            ├── risk_score
            ├── endpoint
            └── device_id

Device identification does NOT create a separate RequestLog.

RequestLog remains the canonical source for API usage and
billing metering.

RiskScore is intentionally retained at this stage. Its removal
will only be considered after all application imports and
dependencies have been verified.
============================================================
"""

from app.models.user import User
from app.models.api_key import APIKey
from app.models.request_log import RequestLog
from app.models.risk_score import RiskScore
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.device_fingerprint import DeviceFingerprint


# ============================================================
# PUBLIC MODEL EXPORTS
# ============================================================

__all__ = [
    "User",
    "APIKey",
    "RequestLog",
    "RiskScore",
    "Plan",
    "Subscription",
    "DeviceFingerprint",
]