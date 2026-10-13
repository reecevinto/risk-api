from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models.request_log import RequestLog


BEHAVIOR_HISTORY_LIMIT = 20

RAPID_REQUEST_THRESHOLD_SECONDS = 5
TIMING_SCORE_MAX = 15

VELOCITY_SCORE_MAX = 40
BURST_WINDOW_SECONDS = 10
BURST_REQUEST_THRESHOLD = 5

SESSION_WINDOW_SECONDS = 900
SESSION_DEVICE_CHANGE_SCORE = 12
SESSION_IP_CHANGE_SCORE = 8
SESSION_MAX_SCORE = 20


def analyze_request_timing(timestamps: List[datetime]) -> dict:
    """
    Analyze the timing between recent requests.

    Returns:
        {
            "score": int,
            "flags": list[str]
        }
    """

    if len(timestamps) < 2:
        return {
            "score": 0,
            "flags": [],
        }

    ordered_timestamps = sorted(timestamps)

    intervals = [
        (current - previous).total_seconds()
        for previous, current in zip(
            ordered_timestamps,
            ordered_timestamps[1:],
        )
    ]

    rapid_intervals = [
        interval
        for interval in intervals
        if interval < RAPID_REQUEST_THRESHOLD_SECONDS
    ]

    if not rapid_intervals:
        return {
            "score": 0,
            "flags": [],
        }

    rapid_ratio = len(rapid_intervals) / len(intervals)

    score = max(
        1,
        min(
            TIMING_SCORE_MAX,
            round(TIMING_SCORE_MAX * rapid_ratio),
        ),
    )

    return {
        "score": score,
        "flags": ["rapid_request_timing"],
    }


def analyze_request_velocity(timestamps: List[datetime]) -> dict:
    """
    Analyze request velocity within a short rolling window.

    A burst is detected when the number of requests occurring
    within BURST_WINDOW_SECONDS reaches BURST_REQUEST_THRESHOLD.

    Returns:
        {
            "score": int,
            "flags": list[str]
        }
    """

    if len(timestamps) < BURST_REQUEST_THRESHOLD:
        return {
            "score": 0,
            "flags": [],
        }

    ordered_timestamps = sorted(timestamps)

    burst_detected = False

    for start_index, start_time in enumerate(ordered_timestamps):
        window_count = 0

        for current_time in ordered_timestamps[start_index:]:
            elapsed = (current_time - start_time).total_seconds()

            if elapsed <= BURST_WINDOW_SECONDS:
                window_count += 1
            else:
                break

        if window_count >= BURST_REQUEST_THRESHOLD:
            burst_detected = True
            break

    if not burst_detected:
        return {
            "score": 0,
            "flags": [],
        }

    return {
        "score": VELOCITY_SCORE_MAX,
        "flags": ["burst_requests"],
    }


def get_recent_request_timestamps(
    db: Session,
    user_id: int,
    limit: int = BEHAVIOR_HISTORY_LIMIT,
) -> List[datetime]:
    """
    Retrieve recent completed request timestamps for a user.

    RequestLog is the canonical source for completed API
    request history.

    The current request is not stored yet when this function
    runs. The production endpoint adds the current request
    timestamp before behavioral analysis.
    """

    logs = (
        db.query(RequestLog.created_at)
        .filter(
            RequestLog.user_id == user_id,
            RequestLog.created_at.isnot(None),
        )
        .order_by(RequestLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        created_at
        for (created_at,) in logs
    ]


def get_recent_request_context(
    db: Session,
    user_id: int,
    limit: int = BEHAVIOR_HISTORY_LIMIT,
) -> List[dict]:
    """
    Retrieve recent completed request context for a user.

    RequestLog is the canonical source for completed request
    history used by session behavior analysis.

    The current request is not included because it has not been
    persisted yet when behavioral analysis runs.

    Returns:
        [
            {
                "device_id": int | None,
                "ip": str | None,
                "created_at": datetime,
            }
        ]
    """

    logs = (
        db.query(
            RequestLog.device_id,
            RequestLog.ip,
            RequestLog.created_at,
        )
        .filter(
            RequestLog.user_id == user_id,
            RequestLog.created_at.isnot(None),
        )
        .order_by(RequestLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "device_id": device_id,
            "ip": ip,
            "created_at": created_at,
        }
        for device_id, ip, created_at in logs
    ]

def analyze_session_behavior(
    previous_requests: list[dict],
    current_device_id: int | None,
    current_ip: str | None,
    current_time: datetime,
) -> dict:
    """
    Analyze continuity of the current request with the
    most recent request inside the active session window.

    Session behavior is based on:
        - device continuity
        - IP continuity

    Scoring:
        device change = +12
        IP change     = +8
        maximum       = 20

    A previous request is considered part of the active
    session only when it occurred within SESSION_WINDOW_SECONDS.

    Unknown previous device identifiers do not create a
    device-change penalty.

    Returns:
        {
            "session_risk_score": int,
            "session_flags": list[str]
        }
    """

    if not previous_requests:
        return {
            "session_risk_score": 0,
            "session_flags": [],
        }

    ordered_requests = sorted(
        previous_requests,
        key=lambda request: request["created_at"],
        reverse=True,
    )

    most_recent_request = ordered_requests[0]

    previous_time = most_recent_request["created_at"]

    elapsed_seconds = (
        current_time - previous_time
    ).total_seconds()

    if elapsed_seconds > SESSION_WINDOW_SECONDS:
        return {
            "session_risk_score": 0,
            "session_flags": [],
        }

    session_risk_score = 0
    session_flags = []

    previous_device_id = most_recent_request.get("device_id")
    previous_ip = most_recent_request.get("ip")

    if (
        previous_device_id is not None
        and current_device_id != previous_device_id
    ):
        session_risk_score += SESSION_DEVICE_CHANGE_SCORE
        session_flags.append("device_change")

    if current_ip != previous_ip:
        session_risk_score += SESSION_IP_CHANGE_SCORE
        session_flags.append("ip_change")

    session_risk_score = min(
        SESSION_MAX_SCORE,
        session_risk_score,
    )

    return {
        "session_risk_score": session_risk_score,
        "session_flags": session_flags,
    }


def analyze_behavior(
    timestamps: List[datetime],
) -> dict:
    """
    Combine request-timing and request-velocity signals.

    Current Day 9.3 scoring:
        timing   = 0-15
        velocity = 0-40
        total    = 0-55

    Session behavior is intentionally not included yet.

    Returns:
        {
            "behavior_risk_score": int,
            "behavior_flags": list[str]
        }
    """

    timing_result = analyze_request_timing(timestamps)

    velocity_result = analyze_request_velocity(timestamps)

    behavior_risk_score = (
        timing_result["score"]
        + velocity_result["score"]
    )

    behavior_flags = (
        timing_result["flags"]
        + velocity_result["flags"]
    )

    return {
        "behavior_risk_score": behavior_risk_score,
        "behavior_flags": behavior_flags,
    }