"""
============================================================
REQUEST LOGGING SERVICE
============================================================

Purpose
-------
Centralizes persistence of completed API requests.

Responsibilities
----------------
✓ Persist completed risk API requests
✓ Store risk analysis results
✓ Track endpoint usage
✓ Track normal vs overage requests
✓ Associate requests with the device that generated them
✓ Provide source data for usage metering and analytics

Important Architecture
-----------------------
One API request produces exactly ONE RequestLog row.

Device intelligence does NOT create a separate RequestLog.

Therefore:

    /risk/score request
            │
            ├── billing validation
            │
            ├── rate limiting
            │
            ├── device identification
            │
            ├── risk analysis
            │
            └── ONE RequestLog
                    │
                    ├── user_id
                    ├── endpoint
                    ├── risk data
                    ├── billing/overage data
                    └── device_id

Billing / metering continues to use RequestLog records.

DeviceFingerprint.request_count is device telemetry only
and is NOT a second billing counter.

Device identification therefore does NOT call this service
and does NOT create an additional RequestLog.

This service intentionally contains NO FastAPI code.

============================================================
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.request_log import RequestLog


# ============================================================
# LOG REQUEST
# ============================================================

def log_request(
    db: Session,
    user_id: int,
    email: str | None,
    phone: str | None,
    ip: str | None,
    risk: dict[str, Any],
    endpoint: str = "/risk/score",
    is_overage: bool = False,
    device_id: int | None = None,
) -> RequestLog:
    """
    Persist exactly one completed API request.

    Parameters
    ----------
    db
        Active SQLAlchemy database session.

    user_id
        ID of the authenticated user who made the request.

    email
        Email value submitted to the risk endpoint.

    phone
        Phone value submitted to the risk endpoint.

    ip
        IP value submitted to the risk endpoint.

    risk
        Risk engine result dictionary.

        Expected values may include:

            risk_score
            trust_level
            flags

    endpoint
        API endpoint that generated the request.

        Defaults to:

            /risk/score

    is_overage
        Whether the request is classified as an overage
        request for billing purposes.

    device_id
        ID of the DeviceFingerprint associated with the request.

        This creates the relationship:

            RequestLog.device_id
                    │
                    ▼
            DeviceFingerprint.id

        It does NOT create another RequestLog.

    Returns
    -------
    RequestLog
        The persisted request-log record.

    Architecture
    ------------
    RequestLog remains the canonical source for:

        • API usage
        • billing metering
        • endpoint analytics
        • risk-request history

    DeviceFingerprint.request_count remains separate and
    represents device activity only.
    """

    # ========================================================
    # BUILD REQUEST LOG
    # ========================================================

    log = RequestLog(
        # ====================================================
        # USER
        # ====================================================

        user_id=user_id,

        # ====================================================
        # ORIGINAL REQUEST INPUTS
        # ====================================================

        email=email,
        phone=phone,
        ip=ip,

        # ====================================================
        # ENDPOINT TRACKING
        # ====================================================

        endpoint=endpoint,

        # ====================================================
        # RISK ENGINE RESULTS
        # ====================================================

        risk_score=risk.get("risk_score"),
        trust_level=risk.get("trust_level"),
        flags=risk.get("flags"),

        # ====================================================
        # DEVICE INTELLIGENCE
        # ====================================================
        #
        # Associate this request with the DeviceFingerprint
        # that generated it.
        #
        # IMPORTANT:
        #
        # This is only a foreign-key association.
        #
        # It does NOT:
        #
        #   • create another RequestLog
        #   • create another billable request
        #   • affect RequestLog-based metering
        #
        # The device service is responsible only for device
        # identification and DeviceFingerprint activity.
        #

        device_id=device_id,

        # ====================================================
        # DAY 6 PHASE 2
        # OVERAGE TRACKING
        # ====================================================

        is_overage=is_overage,
    )

    # ========================================================
    # PERSIST
    # ========================================================

    db.add(log)

    db.commit()

    db.refresh(log)

    return log