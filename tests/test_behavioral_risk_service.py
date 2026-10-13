from datetime import datetime, timedelta, timezone

from app.services.behavioral_risk_service import (
    analyze_behavior,
    analyze_request_timing,
    analyze_request_velocity,
    analyze_session_behavior,
    get_recent_request_context,
)


def test_normal_request_timing_has_no_rapid_timing_flag():
    timestamps = [
        datetime(2026, 9, 10, 9, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 1, 30, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 4, 0, tzinfo=timezone.utc),
    ]

    result = analyze_request_timing(timestamps)

    assert result["score"] >= 0
    assert result["score"] <= 15
    assert "rapid_request_timing" not in result["flags"]


def test_rapid_request_timing_increases_behavioral_risk():
    timestamps = [
        datetime(2026, 9, 10, 9, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 1, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 2, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 3, tzinfo=timezone.utc),
    ]

    result = analyze_request_timing(timestamps)

    assert result["score"] > 0
    assert "rapid_request_timing" in result["flags"]


def test_empty_request_history_has_zero_timing_risk():
    result = analyze_request_timing([])

    assert result["score"] == 0
    assert result["flags"] == []


def test_normal_velocity_has_no_burst_flag():
    request_timestamps = [
        datetime(2026, 9, 10, 9, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 15, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 30, tzinfo=timezone.utc),
    ]

    result = analyze_request_velocity(request_timestamps)

    assert result["score"] == 0
    assert result["flags"] == []


def test_burst_velocity_increases_behavioral_risk():
    request_timestamps = [
        datetime(2026, 9, 10, 9, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 1, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 2, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 3, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 4, tzinfo=timezone.utc),
    ]

    result = analyze_request_velocity(request_timestamps)

    assert result["score"] > 0
    assert result["score"] <= 40
    assert "burst_requests" in result["flags"]


def test_velocity_with_no_requests_has_zero_risk():
    result = analyze_request_velocity([])

    assert result["score"] == 0
    assert result["flags"] == []


def test_combined_behavioral_analysis_returns_zero_for_normal_requests():
    timestamps = [
        datetime(2026, 9, 10, 9, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 1, 30, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 4, 0, tzinfo=timezone.utc),
    ]

    result = analyze_behavior(timestamps)

    assert result["behavior_risk_score"] == 0
    assert result["behavior_flags"] == []


def test_combined_behavioral_analysis_detects_timing_and_velocity():
    timestamps = [
        datetime(2026, 9, 10, 9, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 1, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 2, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 3, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 9, 0, 4, tzinfo=timezone.utc),
    ]

    result = analyze_behavior(timestamps)

    assert result["behavior_risk_score"] == 55
    assert "rapid_request_timing" in result["behavior_flags"]
    assert "burst_requests" in result["behavior_flags"]


# ---------------------------------------------------------------------------
# Day 9.5 — Session Behavior Profiling
# ---------------------------------------------------------------------------


def test_session_with_no_previous_requests_has_zero_risk():
    current_time = datetime(2026, 9, 29, 6, 32, 56, tzinfo=timezone.utc)

    result = analyze_session_behavior(
        previous_requests=[],
        current_device_id=1,
        current_ip="8.8.8.8",
        current_time=current_time,
    )

    assert result["session_risk_score"] == 0
    assert result["session_flags"] == []


def test_session_with_same_device_and_ip_has_zero_risk():
    current_time = datetime(2026, 9, 29, 6, 32, 56, tzinfo=timezone.utc)

    previous_requests = [
        {
            "device_id": 1,
            "ip": "8.8.8.8",
            "created_at": current_time - timedelta(seconds=30),
        }
    ]

    result = analyze_session_behavior(
        previous_requests=previous_requests,
        current_device_id=1,
        current_ip="8.8.8.8",
        current_time=current_time,
    )

    assert result["session_risk_score"] == 0
    assert result["session_flags"] == []


def test_session_detects_device_change():
    current_time = datetime(2026, 9, 29, 6, 32, 56, tzinfo=timezone.utc)

    previous_requests = [
        {
            "device_id": 1,
            "ip": "8.8.8.8",
            "created_at": current_time - timedelta(seconds=30),
        }
    ]

    result = analyze_session_behavior(
        previous_requests=previous_requests,
        current_device_id=2,
        current_ip="8.8.8.8",
        current_time=current_time,
    )

    assert result["session_risk_score"] == 12
    assert "device_change" in result["session_flags"]
    assert "ip_change" not in result["session_flags"]


def test_session_detects_ip_change():
    current_time = datetime(2026, 9, 29, 6, 32, 56, tzinfo=timezone.utc)

    previous_requests = [
        {
            "device_id": 1,
            "ip": "8.8.8.8",
            "created_at": current_time - timedelta(seconds=30),
        }
    ]

    result = analyze_session_behavior(
        previous_requests=previous_requests,
        current_device_id=1,
        current_ip="1.1.1.1",
        current_time=current_time,
    )

    assert result["session_risk_score"] == 8
    assert "ip_change" in result["session_flags"]
    assert "device_change" not in result["session_flags"]


def test_session_detects_device_and_ip_change():
    current_time = datetime(2026, 9, 29, 6, 32, 56, tzinfo=timezone.utc)

    previous_requests = [
        {
            "device_id": 1,
            "ip": "8.8.8.8",
            "created_at": current_time - timedelta(seconds=30),
        }
    ]

    result = analyze_session_behavior(
        previous_requests=previous_requests,
        current_device_id=2,
        current_ip="1.1.1.1",
        current_time=current_time,
    )

    assert result["session_risk_score"] == 20
    assert "device_change" in result["session_flags"]
    assert "ip_change" in result["session_flags"]


def test_session_ignores_requests_outside_session_window():
    current_time = datetime(2026, 9, 29, 6, 32, 56, tzinfo=timezone.utc)

    previous_requests = [
        {
            "device_id": 1,
            "ip": "8.8.8.8",
            "created_at": current_time - timedelta(minutes=16),
        }
    ]

    result = analyze_session_behavior(
        previous_requests=previous_requests,
        current_device_id=2,
        current_ip="1.1.1.1",
        current_time=current_time,
    )

    assert result["session_risk_score"] == 0
    assert result["session_flags"] == []


def test_session_does_not_assume_device_change_when_previous_device_is_unknown():
    current_time = datetime(2026, 9, 29, 6, 32, 56, tzinfo=timezone.utc)

    previous_requests = [
        {
            "device_id": None,
            "ip": "8.8.8.8",
            "created_at": current_time - timedelta(seconds=30),
        }
    ]

    result = analyze_session_behavior(
        previous_requests=previous_requests,
        current_device_id=1,
        current_ip="8.8.8.8",
        current_time=current_time,
    )

    assert result["session_risk_score"] == 0
    assert result["session_flags"] == []


def test_session_uses_most_recent_request_for_continuity():
    current_time = datetime(2026, 9, 29, 6, 32, 56, tzinfo=timezone.utc)

    previous_requests = [
        {
            "device_id": 1,
            "ip": "8.8.8.8",
            "created_at": current_time - timedelta(minutes=5),
        },
        {
            "device_id": 2,
            "ip": "1.1.1.1",
            "created_at": current_time - timedelta(seconds=30),
        },
    ]

    result = analyze_session_behavior(
        previous_requests=previous_requests,
        current_device_id=2,
        current_ip="1.1.1.1",
        current_time=current_time,
    )

    assert result["session_risk_score"] == 0
    assert result["session_flags"] == []

from unittest.mock import MagicMock


def test_get_recent_request_context_retrieves_device_ip_and_created_at():
    first_time = datetime(
        2026,
        9,
        29,
        6,
        32,
        56,
        tzinfo=timezone.utc,
    )

    second_time = datetime(
        2026,
        9,
        29,
        6,
        31,
        56,
        tzinfo=timezone.utc,
    )

    db = MagicMock()

    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        (1, "8.8.8.8", first_time),
        (2, "1.1.1.1", second_time),
    ]

    result = get_recent_request_context(
        db=db,
        user_id=1,
    )

    assert result == [
        {
            "device_id": 1,
            "ip": "8.8.8.8",
            "created_at": first_time,
        },
        {
            "device_id": 2,
            "ip": "1.1.1.1",
            "created_at": second_time,
        },
    ]


def test_get_recent_request_context_orders_results_newest_first():
    db = MagicMock()

    query = (
        db.query.return_value
        .filter.return_value
    )

    ordered_query = query.order_by.return_value
    ordered_query.limit.return_value.all.return_value = []

    get_recent_request_context(
        db=db,
        user_id=1,
    )

    order_by_call = query.order_by.call_args

    assert order_by_call is not None
    assert "created_at DESC" in str(order_by_call.args[0])


def test_get_recent_request_context_respects_requested_limit():
    db = MagicMock()

    query = (
        db.query.return_value
        .filter.return_value
        .order_by.return_value
    )

    query.limit.return_value.all.return_value = []

    get_recent_request_context(
        db=db,
        user_id=1,
        limit=5,
    )

    query.limit.assert_called_once_with(5)


def test_get_recent_request_context_scopes_results_to_user():
    db = MagicMock()

    query = (
        db.query.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
    )

    query.all.return_value = []

    get_recent_request_context(
        db=db,
        user_id=42,
    )

    filter_call = db.query.return_value.filter.call_args

    assert filter_call is not None

    filter_expression = filter_call.args[0]

    assert "request_logs.user_id" in str(filter_expression)

    compiled_expression = filter_expression.compile(
        compile_kwargs={"literal_binds": True}
    )

    assert "42" in str(compiled_expression)


def test_get_recent_request_context_excludes_missing_created_at():
    db = MagicMock()

    query = (
        db.query.return_value
        .filter.return_value
        .order_by.return_value
        .limit.return_value
    )

    query.all.return_value = []

    get_recent_request_context(
        db=db,
        user_id=1,
    )

    filter_call = db.query.return_value.filter.call_args

    assert filter_call is not None

    filter_expressions = filter_call.args

    assert any(
        "created_at IS NOT NULL" in str(expression)
        for expression in filter_expressions
    )