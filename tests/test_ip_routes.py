from types import SimpleNamespace

from app.api.routes import ip as ip_route
from app.api.routes import risk as risk_route


def make_user():
    return SimpleNamespace(id=123, email="route-test@example.com")


def test_ip_route_returns_ip_intelligence_result(monkeypatch):
    expected_result = {
        "ip": "8.8.8.8",
        "status": "ok",
        "country": "United States",
        "country_code": "US",
        "is_vpn": True,
        "is_proxy": True,
        "risk_flag": "high",
    }
    calls = []

    def fake_analyze_ip(ip):
        calls.append(ip)
        return expected_result

    monkeypatch.setattr(ip_route, "analyze_ip", fake_analyze_ip)

    response = ip_route.analyze(ip="8.8.8.8", user=make_user())

    assert calls == ["8.8.8.8"]
    assert response["input"] == "8.8.8.8"
    assert response["result"] == expected_result
    assert response["user"] == {
        "id": 123,
        "email": "route-test@example.com",
    }


def test_risk_analyze_route_applies_ip_risk_signals(monkeypatch):
    ip_result = {
        "ip": "8.8.8.8",
        "status": "ok",
        "is_vpn": True,
        "is_proxy": True,
        "is_tor": False,
        "is_relay": False,
        "is_hosting": False,
        "country_mismatch": False,
    }

    monkeypatch.setattr(
        risk_route,
        "analyze_ip",
        lambda ip: ip_result,
    )

    response = risk_route.analyze_risk(
        phone=None,
        email=None,
        ip="8.8.8.8",
        db=object(),
        user=make_user(),
    )

    assert response["input"]["ip"] == "8.8.8.8"
    assert response["risk_analysis"]["risk_score"] == 30
    assert response["risk_analysis"]["trust_level"] == "low"
    assert response["risk_analysis"]["flags"] == ["vpn_detected"]
    assert response["user"]["id"] == 123


def test_production_score_route_integrates_ip_intelligence(monkeypatch):
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from fastapi import Request

    from app.schemas.risky import RiskRequest

    user = SimpleNamespace(
        id=123,
        email="route-test@example.com",
        plan_id=1,
    )

    device = SimpleNamespace(
        id=456,
        browser="Test Browser",
        browser_version="1.0",
        os="Test OS",
        os_version="1.0",
        platform="Desktop",
        language="en",
        timezone="UTC",
        screen_resolution="1920x1080",
        first_seen=None,
        last_seen=None,
        request_count=1,
        is_trusted=False,
        is_blocked=False,
    )

    ip_result = {
        "ip": "8.8.8.8",
        "status": "ok",
        "is_vpn": True,
        "is_proxy": True,
        "is_tor": False,
        "is_relay": False,
        "is_hosting": False,
        "country_mismatch": False,
    }

    logged_requests = []
    analyzed_ips = []

    monkeypatch.setattr(
        risk_route,
        "can_make_request",
        lambda db, user: True,
    )
    monkeypatch.setattr(
        risk_route,
        "check_rate_limit",
        lambda user_id: True,
    )
    monkeypatch.setattr(
        risk_route,
        "get_or_create_device",
        lambda **kwargs: {
            "device": device,
            "is_new_device": True,
            "device_hash": "test-device-hash",
        },
    )
    monkeypatch.setattr(
        risk_route,
        "analyze_ip",
        lambda ip: analyzed_ips.append(ip) or ip_result,
    )
    monkeypatch.setattr(
        risk_route,
        "get_recent_request_timestamps",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        risk_route,
        "get_recent_request_context",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        risk_route,
        "analyze_behavior",
        lambda timestamps: {
            "behavior_risk_score": 2,
            "behavior_flags": ["test_behavior_flag"],
        },
    )
    monkeypatch.setattr(
        risk_route,
        "analyze_session_behavior",
        lambda **kwargs: {
            "session_risk_score": 3,
            "session_flags": ["test_session_flag"],
        },
    )
    monkeypatch.setattr(
        risk_route,
        "calculate_overage_charge",
        lambda db, user: {
            "is_overage": False,
            "overage_requests": 0,
            "price_per_request": 0,
            "total_charge": 0,
        },
    )
    monkeypatch.setattr(
        risk_route,
        "log_request",
        lambda **kwargs: logged_requests.append(kwargs),
    )
    monkeypatch.setattr(
        risk_route,
        "get_current_usage",
        lambda db, user: 1,
    )
    monkeypatch.setattr(
        risk_route,
        "get_plan_limit",
        lambda user: 100,
    )

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/risk/score",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 12345),
            "query_string": b"",
            "headers": [(b"user-agent", b"pytest")],
        }
    )

    response = risk_route.score_risk(
        payload=RiskRequest(ip="8.8.8.8"),
        request=request,
        db=object(),
        user=user,
    )

    assert analyzed_ips == ["8.8.8.8"]
    assert response["ip_analysis"] == ip_result
    assert response["risk_analysis"]["risk_score"] == 30
    assert response["risk_analysis"]["flags"] == ["vpn_detected"]
    assert response["behavior_risk_score"] == 5
    assert response["behavior_flags"] == [
        "test_behavior_flag",
        "test_session_flag",
    ]
    assert response["device"]["id"] == device.id
    assert response["billing"]["usage"] == 1
    assert len(logged_requests) == 1
    assert logged_requests[0]["user_id"] == user.id
    assert logged_requests[0]["device_id"] == device.id
