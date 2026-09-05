"""
============================================================
DAY 8 — PHASE 3
DEVICE INTELLIGENCE SERVICE
============================================================

Purpose
-------
This service performs fraud intelligence using stored
DeviceFingerprint records.

Unlike device_fingerprint_service.py, this service does NOT
generate fingerprints.

Instead, it analyzes previously stored device fingerprints to
detect and report:

    • Known devices
    • New/untrusted devices
    • Returning devices
    • Shared-device signals
    • Device reputation
    • Device history
    • Suspicious device activity
    • User device statistics

This becomes the foundation for future:

    ✓ Bot detection
    ✓ Multi-account detection
    ✓ Account takeover detection
    ✓ Device reputation scoring
    ✓ Impossible-travel detection
    ✓ Session intelligence
    ✓ Behavioral analysis

IMPORTANT ARCHITECTURE
----------------------
This service uses the CURRENT DeviceFingerprint schema.

Canonical device identity field:

    device_hash

Canonical device metadata:

    browser
    browser_version
    os
    os_version
    platform
    language
    timezone
    screen_resolution

Canonical activity fields:

    first_seen
    last_seen
    request_count

Canonical security fields:

    is_trusted
    is_blocked

Legacy names such as:

    fingerprint_hash
    session_count
    user_agent
    ip_address

are NOT used.

IMPORTANT SHARED-DEVICE NOTE
----------------------------
The current DeviceFingerprint schema still has a UNIQUE
constraint on device_hash.

Therefore, the current database can represent one
DeviceFingerprint row per unique device_hash.

The shared-device methods below intentionally remain part of
the intelligence layer because shared-device detection is part
of the target architecture.

However, until the later device-identity architecture phase
introduces a proper user ↔ device association model, the
current UNIQUE device_hash constraint limits how many users can
be represented against the same physical fingerprint.

This file therefore does NOT attempt to solve that schema
change prematurely.

IMPORTANT BILLING RULE
----------------------
Device intelligence does NOT create RequestLog records.

RequestLog remains the canonical source for API usage and
billing metering.

DeviceFingerprint.request_count is device telemetry only.

This service intentionally contains NO FastAPI code.
============================================================
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.device_fingerprint import DeviceFingerprint


class DeviceIntelligenceService:
    """
    Performs analytics and intelligence operations on stored
    device fingerprints.
    """

    # ==========================================================
    # CHECK WHETHER A DEVICE HAS EVER BEEN SEEN
    # ==========================================================

    @staticmethod
    def fingerprint_exists(
        db: Session,
        device_hash: str,
    ) -> bool:
        """
        Return True if the specified device hash exists.

        Useful for:

            • First-device detection
            • Returning-device detection
            • Device reputation checks
        """

        if not device_hash:
            return False

        return (
            db.query(DeviceFingerprint)
            .filter(
                DeviceFingerprint.device_hash == device_hash
            )
            .first()
            is not None
        )

    # ==========================================================
    # COUNT USERS ASSOCIATED WITH A DEVICE
    # ==========================================================

    @staticmethod
    def users_using_device(
        db: Session,
        device_hash: str,
    ) -> int:
        """
        Count the number of unique users associated with a
        device hash.

        Intended future intelligence:

            1 user
                → normal

            multiple users
                → potentially shared device

            many users
                → potentially suspicious device reuse

        IMPORTANT
        ---------
        The current DeviceFingerprint model has device_hash
        marked UNIQUE. Therefore, the current schema can only
        represent one DeviceFingerprint row for a given hash.

        This method is intentionally retained because shared
        device detection is part of the target architecture and
        will become meaningful once the user ↔ device association
        architecture is expanded.
        """

        if not device_hash:
            return 0

        return (
            db.query(
                func.count(
                    func.distinct(
                        DeviceFingerprint.user_id
                    )
                )
            )
            .filter(
                DeviceFingerprint.device_hash == device_hash
            )
            .scalar()
            or 0
        )

    # ==========================================================
    # COUNT DEVICES FOR USER
    # ==========================================================

    @staticmethod
    def devices_for_user(
        db: Session,
        user_id: int,
    ) -> int:
        """
        Return the number of unique devices associated with a
        user.
        """

        return (
            db.query(
                func.count(
                    func.distinct(
                        DeviceFingerprint.device_hash
                    )
                )
            )
            .filter(
                DeviceFingerprint.user_id == user_id
            )
            .scalar()
            or 0
        )

    # ==========================================================
    # GET ALL DEVICES FOR USER
    # ==========================================================

    @staticmethod
    def get_user_devices(
        db: Session,
        user_id: int,
    ) -> list[DeviceFingerprint]:
        """
        Return all known devices associated with a user.

        Devices are ordered from most recently active to least
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

    # ==========================================================
    # GET USERS FOR DEVICE
    # ==========================================================

    @staticmethod
    def get_users_for_device(
        db: Session,
        device_hash: str,
    ) -> list[DeviceFingerprint]:
        """
        Return DeviceFingerprint records associated with a
        device hash.

        This method is intentionally retained for future
        shared-device intelligence.

        Under the current UNIQUE device_hash schema, this will
        normally return at most one DeviceFingerprint row.
        """

        if not device_hash:
            return []

        return (
            db.query(DeviceFingerprint)
            .filter(
                DeviceFingerprint.device_hash == device_hash
            )
            .all()
        )

    # ==========================================================
    # DETERMINE WHETHER DEVICE IS SHARED
    # ==========================================================

    @staticmethod
    def is_shared_device(
        db: Session,
        device_hash: str,
        threshold: int = 3,
    ) -> bool:
        """
        Return True when the number of unique users associated
        with a device reaches the supplied threshold.

        Default threshold:

            3 users

        This is a foundation for future:

            • Fraud-farm detection
            • Bot-farm detection
            • Credential-sharing detection
            • Multi-account detection

        NOTE
        ----
        The current UNIQUE device_hash constraint prevents the
        present schema from representing multiple users against
        one hash. The method therefore remains future-ready
        rather than introducing an incorrect schema workaround.
        """

        if threshold < 1:
            threshold = 1

        total_users = (
            DeviceIntelligenceService.users_using_device(
                db,
                device_hash,
            )
        )

        return total_users >= threshold

    # ==========================================================
    # DEVICE REPUTATION
    # ==========================================================

    @staticmethod
    def calculate_device_reputation(
        db: Session,
        device_hash: str,
    ) -> int:
        """
        Calculate a simple device reputation score.

        Score range:

            0   = highest suspicion
            100 = strongest reputation

        Current foundation:

            Start at 100.

            3+ users:
                -20

            10+ users:
                additional -20

        Future reputation inputs can include:

            ✓ VPN history
            ✓ Proxy usage
            ✓ Fraud history
            ✓ Chargebacks
            ✓ Request velocity
            ✓ Geographic switching
            ✓ Account takeover indicators
            ✓ Device blocking history
        """

        if not device_hash:
            return 0

        score = 100

        users = (
            DeviceIntelligenceService.users_using_device(
                db,
                device_hash,
            )
        )

        if users >= 3:
            score -= 20

        if users >= 10:
            score -= 20

        return max(score, 0)

    # ==========================================================
    # ANALYZE DEVICE
    # ==========================================================

    @staticmethod
    def analyze_device(
        db: Session,
        user_id: int,
        device_hash: str,
    ) -> dict[str, Any]:
        """
        Generate an overall device-intelligence report.

        This method does NOT modify the database.

        It provides the foundation for future integration with
        the Risk Intelligence Engine.
        """

        if not device_hash:
            return {
                "known_device": False,
                "shared_device": False,
                "device_reputation": 0,
                "devices_for_user": (
                    DeviceIntelligenceService.devices_for_user(
                        db,
                        user_id,
                    )
                ),
                "users_using_device": 0,
            }

        device_exists = (
            DeviceIntelligenceService.fingerprint_exists(
                db,
                device_hash,
            )
        )

        shared = (
            DeviceIntelligenceService.is_shared_device(
                db,
                device_hash,
            )
        )

        reputation = (
            DeviceIntelligenceService.calculate_device_reputation(
                db,
                device_hash,
            )
        )

        total_devices = (
            DeviceIntelligenceService.devices_for_user(
                db,
                user_id,
            )
        )

        users = (
            DeviceIntelligenceService.users_using_device(
                db,
                device_hash,
            )
        )

        return {
            "known_device": device_exists,
            "shared_device": shared,
            "device_reputation": reputation,
            "devices_for_user": total_devices,
            "users_using_device": users,
        }

    # ==========================================================
    # DASHBOARD SUMMARY
    # ==========================================================

    @staticmethod
    def get_dashboard_summary(
        db: Session,
        user_id: int,
    ) -> dict[str, Any]:
        """
        Aggregate overall device metrics for the user dashboard.
        """

        devices = (
            DeviceIntelligenceService.get_user_devices(
                db,
                user_id,
            )
        )

        total_devices = len(devices)

        trusted_devices = sum(
            1
            for device in devices
            if device.is_trusted
        )

        blocked_devices = sum(
            1
            for device in devices
            if device.is_blocked
        )

        new_devices = sum(
            1
            for device in devices
            if not device.is_trusted
        )

        total_requests = sum(
            device.request_count or 0
            for device in devices
        )

        if total_devices > 0:

            reputation_total = sum(
                DeviceIntelligenceService.calculate_device_reputation(
                    db,
                    device.device_hash,
                )
                for device in devices
            )

            avg_reputation = (
                reputation_total // total_devices
            )

            trust_percentage = (
                trusted_devices / total_devices
            ) * 100

        else:

            avg_reputation = 0
            trust_percentage = 0.0

        return {
            "total_devices": total_devices,
            "trusted_devices": trusted_devices,
            "blocked_devices": blocked_devices,
            "new_devices": new_devices,
            "total_requests": total_requests,
            "average_reputation": avg_reputation,
            "device_trust_percentage": round(
                trust_percentage
            ),
        }

    # ==========================================================
    # KNOWN DEVICES
    # ==========================================================

    @staticmethod
    def get_known_devices(
        db: Session,
        user_id: int,
    ) -> list[dict[str, Any]]:
        """
        Return structured device records for dashboard use.
        """

        devices = (
            DeviceIntelligenceService.get_user_devices(
                db,
                user_id,
            )
        )

        known_devices: list[dict[str, Any]] = []

        for device in devices:

            reputation = (
                DeviceIntelligenceService.calculate_device_reputation(
                    db,
                    device.device_hash,
                )
            )

            shared_users = (
                DeviceIntelligenceService.users_using_device(
                    db,
                    device.device_hash,
                )
            )

            known_devices.append(
                {
                    "id": device.id,

                    "device_hash": device.device_hash,

                    "browser": device.browser,
                    "browser_version": device.browser_version,

                    "os": device.os,
                    "os_version": device.os_version,

                    "platform": device.platform,

                    "screen_resolution": (
                        device.screen_resolution
                    ),

                    "timezone": device.timezone,

                    "language": device.language,

                    "first_seen": (
                        device.first_seen.isoformat()
                        if device.first_seen
                        else None
                    ),

                    "last_seen": (
                        device.last_seen.isoformat()
                        if device.last_seen
                        else None
                    ),

                    "request_count": (
                        device.request_count or 0
                    ),

                    "is_trusted": device.is_trusted,

                    "is_blocked": device.is_blocked,

                    "reputation_score": reputation,

                    "shared_users_count": shared_users,
                }
            )

        return known_devices

    # ==========================================================
    # CURRENT DEVICE
    # ==========================================================

    @staticmethod
    def get_current_device(
        db: Session,
        user_id: int,
        device_hash: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Return a specific device for the user when a hash is
        supplied.

        If no hash is supplied, return the user's most recently
        active device.
        """

        if device_hash:

            device = (
                db.query(DeviceFingerprint)
                .filter(
                    DeviceFingerprint.user_id == user_id,
                    DeviceFingerprint.device_hash == device_hash,
                )
                .first()
            )

        else:

            device = (
                db.query(DeviceFingerprint)
                .filter(
                    DeviceFingerprint.user_id == user_id
                )
                .order_by(
                    desc(
                        DeviceFingerprint.last_seen
                    )
                )
                .first()
            )

        if not device:
            return None

        reputation = (
            DeviceIntelligenceService.calculate_device_reputation(
                db,
                device.device_hash,
            )
        )

        return {
            "id": device.id,

            "device_hash": device.device_hash,

            "browser": device.browser,
            "browser_version": device.browser_version,

            "os": device.os,
            "os_version": device.os_version,

            "platform": device.platform,

            "language": device.language,

            "timezone": device.timezone,

            "screen_resolution": device.screen_resolution,

            "first_seen": (
                device.first_seen.isoformat()
                if device.first_seen
                else None
            ),

            "last_seen": (
                device.last_seen.isoformat()
                if device.last_seen
                else None
            ),

            "request_count": (
                device.request_count or 0
            ),

            "is_trusted": device.is_trusted,

            "is_blocked": device.is_blocked,

            "reputation_score": reputation,
        }

    # ==========================================================
    # DEVICE TIMELINE
    # ==========================================================

    @staticmethod
    def get_device_timeline(
        db: Session,
        user_id: int,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Return the user's most recently active devices.

        The timeline is ordered by last_seen descending.
        """

        if limit < 1:
            limit = 1

        devices = (
            db.query(DeviceFingerprint)
            .filter(
                DeviceFingerprint.user_id == user_id
            )
            .order_by(
                desc(
                    DeviceFingerprint.last_seen
                )
            )
            .limit(limit)
            .all()
        )

        timeline: list[dict[str, Any]] = []

        for device in devices:

            if device.is_blocked:
                status = "Blocked"

            elif device.is_trusted:
                status = "Trusted"

            else:
                status = "New"

            timeline.append(
                {
                    "device_id": device.id,

                    "browser": device.browser,
                    "browser_version": device.browser_version,

                    "os": device.os,
                    "os_version": device.os_version,

                    "platform": device.platform,

                    "status": status,

                    "last_seen": (
                        device.last_seen.isoformat()
                        if device.last_seen
                        else None
                    ),

                    "request_count": (
                        device.request_count or 0
                    ),
                }
            )

        return timeline

    # ==========================================================
    # DEVICE HEALTH
    # ==========================================================

    @staticmethod
    def get_device_health(
        db: Session,
        user_id: int,
    ) -> dict[str, Any]:
        """
        Evaluate the user's registered-device health.

        Current indicators:

            • Blocked devices
            • Shared-device signals
            • Trusted devices
            • New/untrusted devices

        This remains an intelligence/dashboard layer.

        It does NOT modify risk_engine.py yet.
        """

        devices = (
            DeviceIntelligenceService.get_user_devices(
                db,
                user_id,
            )
        )

        total_devices = len(devices)

        if total_devices == 0:
            return {
                "status": "HEALTHY",
                "risk_level": "LOW",
                "suspicious_devices": 0,
                "blocked_devices": 0,
                "trusted_percentage": 0,
                "blocked_percentage": 0,
                "new_percentage": 0,
            }

        suspicious_count = 0
        blocked_count = 0
        trusted_count = 0
        new_count = 0

        for device in devices:

            if device.is_blocked:
                blocked_count += 1

            if device.is_trusted:
                trusted_count += 1
            else:
                new_count += 1

            if (
                DeviceIntelligenceService.is_shared_device(
                    db,
                    device.device_hash,
                )
            ):
                suspicious_count += 1

        if (
            blocked_count > 0
            or suspicious_count > 1
        ):
            risk_level = "HIGH"
            status = "ACTION_REQUIRED"

        elif suspicious_count == 1:
            risk_level = "MEDIUM"
            status = "MONITORING"

        else:
            risk_level = "LOW"
            status = "HEALTHY"

        return {
            "status": status,

            "risk_level": risk_level,

            "suspicious_devices": suspicious_count,

            "blocked_devices": blocked_count,

            "trusted_percentage": round(
                (
                    trusted_count
                    / total_devices
                ) * 100
            ),

            "blocked_percentage": round(
                (
                    blocked_count
                    / total_devices
                ) * 100
            ),

            "new_percentage": round(
                (
                    new_count
                    / total_devices
                ) * 100
            ),
        }