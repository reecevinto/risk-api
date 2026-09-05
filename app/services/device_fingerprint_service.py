"""
============================================================
DAY 8 — PHASE 3 DEVICE FINGERPRINTING SERVICE
============================================================

Purpose
-------
Centralizes all device fingerprint operations.

Responsibilities
----------------
✓ Build deterministic SHA-256 device hashes
✓ Identify known devices
✓ Register new devices
✓ Update device activity
✓ Track device request counts
✓ Store normalized browser/device metadata
✓ Manage device trust
✓ Provide basic anomaly detection

This service intentionally contains NO FastAPI code.

It is reused by:
• Risk Engine
• Authentication
• Fraud Detection
• Device Intelligence
• Dashboard Analytics

IMPORTANT
---------
This service is aligned with the CURRENT DeviceFingerprint model.

Current canonical fields:

device_hash
user_id
browser
browser_version
os
os_version
platform
language
timezone
screen_resolution
first_seen
last_seen
request_count
is_trusted
is_blocked
created_at

This service does NOT store:

user_agent
ip_address
session_count
fingerprint_hash

Those fields do not exist in the current SQLAlchemy model.

============================================================
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.device_fingerprint import DeviceFingerprint


# ============================================================
# FINGERPRINT BUILDER
# ============================================================

def generate_device_hash(
    *,
    user_agent: str,
    accept_language: str,
    screen_resolution: str,
    timezone_name: str,
    platform: str,
) -> str:
    """
    Generate a deterministic SHA-256 device fingerprint.

    The same normalized browser/device characteristics produce
    the same hash.

    The raw User-Agent and other identifying values are NOT
    stored in the database as raw fingerprint data.

    Parameters
    ----------
    user_agent:
        Browser User-Agent string.

    accept_language:
        Browser language, for example: en-US

    screen_resolution:
        Example: 1920x1080

    timezone_name:
        Example: Africa/Nairobi

    platform:
        Example:
        Win32
        Linux x86_64
        MacIntel

    Returns
    -------
    str
        SHA-256 hexadecimal fingerprint.
    """

    payload = {
        "accept_language": (accept_language or "").strip().lower(),
        "platform": (platform or "").strip().lower(),
        "screen_resolution": (screen_resolution or "").strip(),
        "timezone": (timezone_name or "").strip(),
        "user_agent": (user_agent or "").strip(),
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


# ============================================================
# USER AGENT PARSING
# ============================================================

def _parse_browser(user_agent: str) -> tuple[str, str]:
    """
    Extract a basic browser name and version from User-Agent.

    This is intentionally lightweight.

    The raw User-Agent is used to generate the fingerprint hash
    but is NOT stored directly in DeviceFingerprint.
    """

    ua = (user_agent or "").strip()

    browser_patterns = [
        ("Edge", r"(?:Edg|Edge)/([\d.]+)"),
        ("Opera", r"(?:OPR|Opera)/([\d.]+)"),
        ("Chrome", r"(?:Chrome|CriOS)/([\d.]+)"),
        ("Firefox", r"(?:Firefox|FxiOS)/([\d.]+)"),
        ("Safari", r"Version/([\d.]+).*Safari/"),
    ]

    for browser, pattern in browser_patterns:
        match = re.search(
            pattern,
            ua,
            re.IGNORECASE,
        )

        if match:
            return browser, match.group(1)

    if "MSIE" in ua:
        match = re.search(
            r"MSIE\s+([\d.]+)",
            ua,
            re.IGNORECASE,
        )

        if match:
            return "Internet Explorer", match.group(1)

    return "Unknown", ""


def _parse_os(user_agent: str) -> tuple[str, str]:
    """
    Extract a basic operating-system name and version from
    User-Agent.

    The parser is deliberately conservative.
    """

    ua = (user_agent or "").strip()

    # Windows
    match = re.search(
        r"Windows NT ([\d.]+)",
        ua,
        re.IGNORECASE,
    )

    if match:
        windows_versions = {
            "10.0": "10",
            "6.4": "10",
            "6.3": "8.1",
            "6.2": "8",
            "6.1": "7",
        }

        version = windows_versions.get(
            match.group(1),
            match.group(1),
        )

        return "Windows", version

    # Android
    match = re.search(
        r"Android\s+([\d.]+)",
        ua,
        re.IGNORECASE,
    )

    if match:
        return "Android", match.group(1)

    # iOS
    match = re.search(
        r"(?:iPhone OS|CPU OS)\s+([\d_]+)",
        ua,
        re.IGNORECASE,
    )

    if match:
        return "iOS", match.group(1).replace("_", ".")

    # macOS
    match = re.search(
        r"Mac OS X\s*([\d_\.]+)?",
        ua,
        re.IGNORECASE,
    )

    if match:
        version = (match.group(1) or "").replace("_", ".")
        return "macOS", version

    # Linux
    if "Linux" in ua:
        return "Linux", ""

    # ChromeOS
    if "CrOS" in ua:
        match = re.search(
            r"CrOS\s+\S+\s+([\d.]+)",
            ua,
            re.IGNORECASE,
        )

        return "ChromeOS", match.group(1) if match else ""

    return "Unknown", ""


def _normalize_platform(platform: str) -> str:
    """
    Normalize the browser-reported platform into a simple
    Desktop / Mobile / Tablet classification.
    """

    value = (platform or "").strip().lower()

    if any(
        token in value
        for token in (
            "iphone",
            "android",
            "mobile",
        )
    ):
        return "Mobile"

    if "ipad" in value or "tablet" in value:
        return "Tablet"

    if any(
        token in value
        for token in (
            "win",
            "linux",
            "mac",
            "x11",
            "cros",
        )
    ):
        return "Desktop"

    return "Unknown"


# ============================================================
# DEVICE LOOKUP
# ============================================================

def get_device_by_hash(
    db: Session,
    device_hash: str,
) -> DeviceFingerprint | None:
    """
    Retrieve an existing device using its canonical hash.

    The current database schema defines device_hash as UNIQUE,
    therefore lookup is intentionally global rather than
    user-scoped.

    Returns
    -------
    DeviceFingerprint | None
    """

    return (
        db.query(DeviceFingerprint)
        .filter(
            DeviceFingerprint.device_hash == device_hash
        )
        .first()
    )


# ============================================================
# REGISTER NEW DEVICE
# ============================================================

def register_device(
    db: Session,
    *,
    user_id: int,
    device_hash: str,
    user_agent: str,
    accept_language: str,
    screen_resolution: str,
    timezone_name: str,
    platform: str,
) -> DeviceFingerprint:
    """
    Register a brand-new device.

    Only fields that actually exist in the current
    DeviceFingerprint model are persisted.

    The raw User-Agent is never stored directly.
    """

    browser, browser_version = _parse_browser(
        user_agent
    )

    os_name, os_version = _parse_os(
        user_agent
    )

    normalized_platform = _normalize_platform(
        platform
    )

    now = datetime.now(timezone.utc)

    device = DeviceFingerprint(
        user_id=user_id,
        device_hash=device_hash,
        browser=browser,
        browser_version=browser_version,
        os=os_name,
        os_version=os_version,
        platform=normalized_platform,
        language=accept_language or None,
        timezone=timezone_name or None,
        screen_resolution=screen_resolution or None,
        first_seen=now,
        last_seen=now,
        request_count=1,
        is_trusted=False,
        is_blocked=False,
    )

    db.add(device)
    db.commit()
    db.refresh(device)

    return device


# ============================================================
# UPDATE EXISTING DEVICE
# ============================================================

def update_device_activity(
    db: Session,
    device: DeviceFingerprint,
    *,
    user_agent: str | None = None,
    accept_language: str | None = None,
    screen_resolution: str | None = None,
    timezone_name: str | None = None,
    platform: str | None = None,
) -> DeviceFingerprint:
    """
    Update activity for an already-known device.

    Every associated API request increments:

    • request_count
    • last_seen

    Device metadata is refreshed when supplied.

    IMPORTANT
    ---------
    This function does NOT create a RequestLog.

    RequestLog remains the canonical billing/metering source.
    """

    device.request_count = (
        device.request_count or 0
    ) + 1

    device.last_seen = datetime.now(
        timezone.utc
    )

    if user_agent:
        browser, browser_version = _parse_browser(
            user_agent
        )

        os_name, os_version = _parse_os(
            user_agent
        )

        device.browser = browser
        device.browser_version = browser_version
        device.os = os_name
        device.os_version = os_version

    if accept_language:
        device.language = accept_language

    if screen_resolution:
        device.screen_resolution = (
            screen_resolution
        )

    if timezone_name:
        device.timezone = timezone_name

    if platform:
        device.platform = _normalize_platform(
            platform
        )

    db.commit()
    db.refresh(device)

    return device


# ============================================================
# GET OR CREATE DEVICE
# ============================================================

def get_or_create_device(
    db: Session,
    *,
    user_id: int,
    user_agent: str,
    accept_language: str,
    screen_resolution: str,
    timezone_name: str,
    platform: str,
):
    """
    Identify the current device.

    Workflow
    --------
    1. Build deterministic device hash.
    2. Search for the hash.
    3. If the device exists: update activity.
    4. If the device does not exist: register it.

    Returns
    -------
    dict
        {
            "device": DeviceFingerprint,
            "is_new_device": bool,
            "device_hash": str
        }

    IMPORTANT
    ---------
    Device identification does not create a RequestLog.

    The caller is responsible for creating the normal
    RequestLog for the actual API request.
    """

    device_hash = generate_device_hash(
        user_agent=user_agent,
        accept_language=accept_language,
        screen_resolution=screen_resolution,
        timezone_name=timezone_name,
        platform=platform,
    )

    device = get_device_by_hash(
        db,
        device_hash,
    )

    if device is not None:
        update_device_activity(
            db,
            device,
            user_agent=user_agent,
            accept_language=accept_language,
            screen_resolution=screen_resolution,
            timezone_name=timezone_name,
            platform=platform,
        )

        return {
            "device": device,
            "is_new_device": False,
            "device_hash": device_hash,
        }

    device = register_device(
        db=db,
        user_id=user_id,
        device_hash=device_hash,
        user_agent=user_agent,
        accept_language=accept_language,
        screen_resolution=screen_resolution,
        timezone_name=timezone_name,
        platform=platform,
    )

    return {
        "device": device,
        "is_new_device": True,
        "device_hash": device_hash,
    }


# ============================================================
# TRUST MANAGEMENT
# ============================================================

def mark_device_as_trusted(
    db: Session,
    device: DeviceFingerprint,
) -> DeviceFingerprint:
    """
    Mark a device as trusted.
    """

    device.is_trusted = True

    db.commit()
    db.refresh(device)

    return device


def mark_device_as_untrusted(
    db: Session,
    device: DeviceFingerprint,
) -> DeviceFingerprint:
    """
    Remove trusted status from a device.
    """

    device.is_trusted = False

    db.commit()
    db.refresh(device)

    return device


# ============================================================
# BLOCK MANAGEMENT
# ============================================================

def mark_device_as_blocked(
    db: Session,
    device: DeviceFingerprint,
) -> DeviceFingerprint:
    """
    Mark a device as blocked.
    """

    device.is_blocked = True

    db.commit()
    db.refresh(device)

    return device


def mark_device_as_unblocked(
    db: Session,
    device: DeviceFingerprint,
) -> DeviceFingerprint:
    """
    Remove blocked status from a device.
    """

    device.is_blocked = False

    db.commit()
    db.refresh(device)

    return device


# ============================================================
# USER DEVICE STATISTICS
# ============================================================

def get_user_devices(
    db: Session,
    user_id: int,
) -> list[DeviceFingerprint]:
    """
    Return every device currently associated with a user.

    Results are ordered from most recently active to least
    recently active.
    """

    return (
        db.query(DeviceFingerprint)
        .filter(
            DeviceFingerprint.user_id == user_id
        )
        .order_by(
            DeviceFingerprint.last_seen.desc()
        )
        .all()
    )


# ============================================================
# CURRENT DEVICE
# ============================================================

def get_current_device(
    db: Session,
    *,
    user_id: int,
    device_hash: str,
) -> DeviceFingerprint | None:
    """
    Retrieve a device belonging to the specified user.

    This helper is useful for dashboard/device-security
    operations where both user ownership and device identity
    must be checked.
    """

    return (
        db.query(DeviceFingerprint)
        .filter(
            DeviceFingerprint.user_id == user_id,
            DeviceFingerprint.device_hash == device_hash,
        )
        .first()
    )


# ============================================================
# SIMPLE ANOMALY DETECTION
# ============================================================

def is_device_anomalous(
    device: DeviceFingerprint,
) -> bool:
    """
    Basic Day 8 anomaly detection.

    A device is currently considered anomalous when:

    • it is blocked OR
    • it has not been trusted

    Future phases can expand this with:

    ✓ shared-device detection
    ✓ impossible travel
    ✓ browser changes
    ✓ OS changes
    ✓ IP reputation
    ✓ VPN detection
    ✓ TOR detection
    ✓ velocity checks
    ✓ behavioral scoring
    """

    return (
        device.is_blocked
        or not device.is_trusted
    )