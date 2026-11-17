from types import SimpleNamespace

from fastapi import Request

from app.api.routes import phone as phone_route
from app.api.routes import risk as risk_route
from app.schemas.risky import RiskRequest
from app.services.providers.base import ProviderCategory


def make_user():
    return SimpleNamespace(
        id=123,
        email="route-test@example.com",
        plan_id=1,
    )


def make_phone_result():
    return {
        "phone_valid": True,
        "number_possible": True,
        "possibility_reason": "possible",
        "country": "KE",
        "country_calling_code": 254,
        "carrier": "Safaricom",
        "carrier_source": "phonenumbers_metadata",
        "carrier_status": "identified",
        "carrier_limitation": (
            "Static numbering-plan metadata; "
            "does not verify the current operator or live SIM."
        ),
        "risk_flag": "low",
        "line_type": "mobile",
        "number_type": "mobile",
        "is_african_region": True,
        "regional_intelligence": {
            "country_code": "KE",
            "country_calling_code": 254,
            "continent": "Africa",
            "african_region": "Eastern Africa",
            "is_african_region": True,
        },
    }


def make_orchestration_result(
    *,
    phone=None,
    email=None,
    ip=None,
):
    return SimpleNamespace(
        data={
            ProviderCategory.PHONE: phone,
            ProviderCategory.EMAIL: email,
            ProviderCategory.IP: ip,
        }
    )


def test_phone_route_returns_complete_phone_intelligence(monkeypatch):
    expected_result = make_phone_result()
    analyzed_numbers = []

    def fake_analyze_phone(number):
        analyzed_numbers.append(number)
        return expected_result

    monkeypatch.setattr(
        phone_route,
        "analyze_phone",
        fake_analyze_phone,
    )

    response = phone_route.analyze(
        phone="+254712345678",
        user=make_user(),
    )

    assert analyzed_numbers == ["+254712345678"]
    assert response["input"] == "+254712345678"
    assert response["result"] == expected_result
    assert response["result"]["carrier"] == "Safaricom"
    assert response["result"]["line_type"] == "mobile"
    assert response["result"]["regional_intelligence"]["african_region"] == (
        "Eastern Africa"
    )
    assert response["user"] == {
        "id": 123,
        "email": "route-test@example.com",
    }


def test_legacy_risk_analyze_uses_enriched_phone_result(monkeypatch):
    phone_result = make_phone_result()
    orchestration_calls = []

    def fake_analyze_inputs(**kwargs):
        orchestration_calls.append(kwargs)

        return make_orchestration_result(phone=phone_result)

    monkeypatch.setattr(
        risk_route.provider_orchestrator,
        "analyze_inputs",
        fake_analyze_inputs,
    )

    response = risk_route.analyze_risk(
        phone="+254712345678",
        email=None,
        ip=None,
        db=object(),
        user=make_user(),
    )

    assert orchestration_calls == [
        {
            "phone": "+254712345678",
            "email": None,
            "ip": None,
        }
    ]

    assert response["input"]["phone"] == "+254712345678"
    assert response["input"]["email"] is None
    assert response["input"]["ip"] is None
    assert response["risk_analysis"]["risk_score"] == 0
    assert response["risk_analysis"]["fraud_probability"] == 0.0
    assert response["risk_analysis"]["trust_level"] == "high"
    assert response["risk_analysis"]["flags"] == []
    assert response["user"]["id"] == 123


def test_production_score_route_returns_phone_intelligence_and_logs_once(
    monkeypatch,
):
    user = make_user()

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

    phone_result = make_phone_result()
    orchestration_calls = []
    logged_requests = []
    transaction_events = []

    def fake_log_request(**kwargs):
        transaction_events.append("log_request")
        logged_requests.append(kwargs)

    def fake_get_current_usage(db, user):
        transaction_events.append("get_current_usage")
        return 1

    def fake_get_plan_limit(user):
        transaction_events.append("get_plan_limit")
        return 100

    def fake_commit():
        transaction_events.append("commit")

    def fake_analyze_inputs(**kwargs):
        orchestration_calls.append(kwargs)

        return make_orchestration_result(phone=phone_result)

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
        risk_route.provider_orchestrator,
        "analyze_inputs",
        fake_analyze_inputs,
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
            "behavior_risk_score": 0,
            "behavior_flags": [],
        },
    )
    monkeypatch.setattr(
        risk_route,
        "analyze_session_behavior",
        lambda **kwargs: {
            "session_risk_score": 0,
            "session_flags": [],
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
        fake_log_request,
    )
    monkeypatch.setattr(
        risk_route,
        "get_current_usage",
        fake_get_current_usage,
    )
    monkeypatch.setattr(
        risk_route,
        "get_plan_limit",
        fake_get_plan_limit,
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
        payload=RiskRequest(phone="+254712345678"),
        request=request,
        db=SimpleNamespace(commit=fake_commit),
        user=user,
    )

    assert transaction_events == [
        "log_request",
        "get_current_usage",
        "get_plan_limit",
        "commit",
    ]

    assert orchestration_calls == [
        {
            "phone": "+254712345678",
            "email": None,
            "ip": None,
        }
    ]

    assert response["input"]["phone"] == "+254712345678"
    assert response["phone_analysis"] == phone_result
    assert response["phone_analysis"]["carrier"] == "Safaricom"
    assert response["phone_analysis"]["line_type"] == "mobile"
    assert response["phone_analysis"]["regional_intelligence"][
        "african_region"
    ] == "Eastern Africa"

    assert response["risk_analysis"]["risk_score"] == 0
    assert response["risk_analysis"]["fraud_probability"] == 0.0
    assert response["risk_analysis"]["trust_level"] == "high"
    assert response["risk_analysis"]["flags"] == []

    assert len(logged_requests) == 1
    assert logged_requests[0]["user_id"] == user.id
    assert logged_requests[0]["risk"]["risk_score"] == 0
    assert logged_requests[0]["risk"]["trust_level"] == "low"
    assert logged_requests[0]["phone"] == "+254712345678"
    assert logged_requests[0]["device_id"] == device.id
