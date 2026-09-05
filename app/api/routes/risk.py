from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.routes.auth import get_current_user

from app.schemas.risky import RiskRequest

from app.services.phone_service import analyze_phone
from app.services.email_service import analyze_email
from app.services.ip_service import analyze_ip
from app.services.risk_engine import compute_risk
from app.services.log_service import log_request
from app.services.rate_limiter import check_rate_limit

# ============================================================
# DAY 8 — PHASE 3
# DEVICE FINGERPRINTING
# ============================================================

from app.services.device_fingerprint_service import (
    get_or_create_device,
)

# ============================================================
# DAY 4 PHASE 2 — METERED BILLING ENGINE
# ============================================================

from app.services.metering_service import (
    can_make_request,
    get_current_usage,
    get_plan_limit,
)

# ============================================================
# DAY 6 PHASE 2 — OVERAGE ENGINE
# ============================================================

from app.services.overage_service import (
    calculate_overage_charge,
)


router = APIRouter()


# ============================================================
# EXISTING TEST ENDPOINT — KEEP
# ============================================================

@router.get("/analyze")
def analyze_risk(
    phone: str = None,
    email: str = None,
    ip: str = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Existing risk-analysis test endpoint.

    IMPORTANT
    ---------
    This endpoint remains intentionally outside the production
    metering/device request lifecycle.

    The production endpoint is /score.
    """

    phone_data = (
        analyze_phone(phone)
        if phone
        else None
    )

    email_data = (
        analyze_email(email)
        if email
        else None
    )

    ip_data = (
        analyze_ip(ip)
        if ip
        else None
    )

    risk = compute_risk(
        phone_data=phone_data,
        email_data=email_data,
        ip_data=ip_data,
    )

    return {
        "input": {
            "phone": phone,
            "email": email,
            "ip": ip,
        },
        "risk_analysis": risk,
        "user": {
            "id": user.id,
            "email": user.email,
        },
    }


# ============================================================
# MAIN PRODUCTION ENDPOINT
# ============================================================

@router.post("/score")
def score_risk(
    payload: RiskRequest,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Production risk-scoring endpoint.

    Request lifecycle
    -----------------

    1. Validate billing/subscription
    2. Apply rate limit
    3. Identify/create device
    4. Analyze phone/email/IP
    5. Compute risk
    6. Determine overage status
    7. Write exactly ONE RequestLog row
    8. Attach device_id to that RequestLog
    9. Return risk, device, and billing information

    Device identification does NOT create a second
    RequestLog entry and therefore does not create
    additional billable usage.

    IMPORTANT
    ---------
    DeviceFingerprint.request_count and RequestLog usage
    have different purposes.

    RequestLog:
        Canonical billing/metering source.

    DeviceFingerprint.request_count:
        Device activity counter.
    """

    # ========================================================
    # DAY 5 PHASE 2
    # BILLING / SUBSCRIPTION VALIDATION
    # ========================================================

    if not can_make_request(db, user):
        raise HTTPException(
            status_code=403,
            detail="Usage limit exceeded or subscription inactive.",
        )

    # ========================================================
    # STEP 1 — RATE LIMIT
    # ========================================================

    if not check_rate_limit(user.id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
        )

    # ========================================================
    # STEP 2 — DEVICE IDENTIFICATION
    # ========================================================
    #
    # Standard browser headers:
    #
    # User-Agent
    # Accept-Language
    #
    # Optional browser/device telemetry:
    #
    # X-Device-Screen-Resolution
    # X-Device-Timezone
    # X-Device-Platform
    #
    # Missing optional headers are handled safely by the
    # device fingerprint service.
    #
    # IMPORTANT:
    #
    # Device identification does NOT create a RequestLog.
    #
    # It only creates or updates DeviceFingerprint.
    # ========================================================

    user_agent = request.headers.get(
        "user-agent",
        "",
    )

    accept_language = request.headers.get(
        "accept-language",
        "",
    )

    screen_resolution = request.headers.get(
        "x-device-screen-resolution",
        "",
    )

    timezone_name = request.headers.get(
        "x-device-timezone",
        "",
    )

    platform = request.headers.get(
        "x-device-platform",
        "",
    )

    # ========================================================
    # GET OR CREATE DEVICE
    # ========================================================
    #
    # IMPORTANT:
    #
    # The current device_fingerprint_service.py does NOT
    # accept or store an ip_address.
    #
    # DeviceFingerprint currently contains:
    #
    #   device_hash
    #   user_id
    #   browser
    #   browser_version
    #   os
    #   os_version
    #   platform
    #   language
    #   timezone
    #   screen_resolution
    #   first_seen
    #   last_seen
    #   request_count
    #   is_trusted
    #   is_blocked
    #   created_at
    #
    # Therefore no ip_address is passed here.
    # ========================================================

    device_result = get_or_create_device(
        db=db,
        user_id=user.id,
        user_agent=user_agent,
        accept_language=accept_language,
        screen_resolution=screen_resolution,
        timezone_name=timezone_name,
        platform=platform,
    )

    device = device_result["device"]

    is_new_device = device_result["is_new_device"]

    device_hash = device_result["device_hash"]

    # ========================================================
    # STEP 3 — ANALYZE INPUTS
    # ========================================================

    phone_data = (
        analyze_phone(payload.phone)
        if payload.phone
        else None
    )

    email_data = (
        analyze_email(payload.email)
        if payload.email
        else None
    )

    ip_data = (
        analyze_ip(payload.ip)
        if payload.ip
        else None
    )

    # ========================================================
    # STEP 4 — COMPUTE RISK
    # ========================================================
    #
    # Device reputation is intentionally NOT added to the
    # risk engine yet.
    #
    # Phase 3 first establishes reliable device identity and
    # request linkage.
    #
    # Device risk contribution will be introduced only after
    # the underlying device data is proven reliable.
    # ========================================================

    risk = compute_risk(
        phone_data=phone_data,
        email_data=email_data,
        ip_data=ip_data,
    )

    # ========================================================
    # DAY 6
    # DETERMINE WHETHER THIS REQUEST IS AN OVERAGE REQUEST
    # BEFORE LOGGING
    # ========================================================

    overage = calculate_overage_charge(db, user)

    overage_request = overage["is_overage"]

    # ========================================================
    # STEP 5 — LOG REQUEST
    # ========================================================
    #
    # IMPORTANT:
    #
    # Exactly ONE RequestLog is created for this API request.
    #
    # Device identification above does NOT create a
    # RequestLog.
    #
    # device_id links this request to the corresponding
    # DeviceFingerprint record.
    #
    # RequestLog remains the canonical billing/metering source.
    # ========================================================

    log_request(
        db=db,
        user_id=user.id,
        email=payload.email,
        phone=payload.phone,
        ip=payload.ip,
        risk=risk,
        is_overage=overage_request,
        device_id=device.id,
    )

    # ========================================================
    # STEP 6 — METERED BILLING
    # ========================================================

    current_usage = get_current_usage(
        db,
        user,
    )

    usage_limit = get_plan_limit(
        user,
    )

    # ========================================================
    # STEP 7 — RESPONSE
    # ========================================================

    return {
        "input": payload.dict(),

        # ====================================================
        # RISK ANALYSIS
        # ====================================================

        "phone_analysis": phone_data,

        "email_analysis": email_data,

        "ip_analysis": ip_data,

        "risk_analysis": risk,

        # ====================================================
        # DEVICE INTELLIGENCE
        # ====================================================

        "device": {
            "id": device.id,

            "device_hash": device_hash,

            "is_new_device": is_new_device,

            "browser": device.browser,

            "browser_version": device.browser_version,

            "os": device.os,

            "os_version": device.os_version,

            "platform": device.platform,

            "language": device.language,

            "timezone": device.timezone,

            "screen_resolution": device.screen_resolution,

            "first_seen": device.first_seen,

            "last_seen": device.last_seen,

            "request_count": device.request_count,

            "is_trusted": device.is_trusted,

            "is_blocked": device.is_blocked,

        },

        # ====================================================
        # BILLING
        # ====================================================

        "billing": {
            "plan_id": user.plan_id,

            "usage": current_usage,

            "usage_limit": usage_limit,

            "remaining": max(
                0,
                usage_limit - current_usage,
            ),

            "is_overage_request": overage_request,

            "overage_requests": overage[
                "overage_requests"
            ],

            "overage_price_per_request": overage[
                "price_per_request"
            ],

            "current_overage_charge": overage[
                "total_charge"
            ],
        },

        # ====================================================
        # USER
        # ====================================================

        "user": {
            "id": user.id,

            "email": user.email,
        },
    }