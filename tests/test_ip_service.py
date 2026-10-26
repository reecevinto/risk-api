import requests

from app.services import ip_service


def make_ipinfo_response(
    *,
    anonymous=None,
    is_hosting=False,
    network_type="isp",
    country="United States",
    country_code="US",
):
    """Build a representative IPinfo Plus response for mocked tests."""
    if anonymous is None:
        anonymous = {
            "is_proxy": False,
            "is_vpn": False,
            "is_tor": False,
            "is_relay": False,
        }

    return {
        "geo": {
            "country": country,
            "country_code": country_code,
            "region": "California",
            "city": "Los Angeles",
        },
        "as": {
            "asn": "AS15169",
            "name": "Google LLC",
            "type": network_type,
        },
        "anonymous": anonymous,
        "is_anonymous": any(
            anonymous.get(field) is True
            for field in (
                "is_proxy",
                "is_vpn",
                "is_tor",
                "is_relay",
            )
        ),
        "is_hosting": is_hosting,
        "is_mobile": False,
        "is_anycast": False,
        "is_satellite": False,
    }


class FakeResponse:
    def __init__(self, data=None, status_code=200, json_error=None):
        self.data = data
        self.status_code = status_code
        self.json_error = json_error

    def raise_for_status(self):
        if self.status_code >= 400:
            response = requests.Response()
            response.status_code = self.status_code
            raise requests.HTTPError(
                f"HTTP {self.status_code}",
                response=response,
            )

    def json(self):
        if self.json_error is not None:
            raise self.json_error

        return self.data


def configure_ipinfo(monkeypatch):
    monkeypatch.setattr(
        ip_service.config,
        "IPINFO_TOKEN",
        "test-token",
    )
    monkeypatch.setattr(
        ip_service.config,
        "IPINFO_TIMEOUT_SECONDS",
        3.0,
    )


def test_analyze_ip_returns_geolocation_and_network_details(monkeypatch):
    configure_ipinfo(monkeypatch)

    expected_data = make_ipinfo_response()
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(expected_data)

    monkeypatch.setattr(ip_service.requests, "get", fake_get)

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["status"] == "ok"
    assert result["error_code"] is None
    assert result["country"] == "United States"
    assert result["country_code"] == "US"
    assert result["region"] == "California"
    assert result["city"] == "Los Angeles"
    assert result["isp"] == "Google LLC"
    assert result["organization"] == "Google LLC"
    assert result["asn"] == "AS15169"
    assert result["network_type"] == "isp"
    assert result["is_hosting"] is False
    assert result["is_residential"] is None
    assert result["risk_flag"] == "low"

    assert len(calls) == 1

    url, kwargs = calls[0]
    assert url == "https://api.ipinfo.io/lookup/8.8.8.8"
    assert kwargs["params"] == {"token": "test-token"}
    assert kwargs["timeout"] == 3.0


def test_analyze_ip_detects_vpn_separately_from_generic_proxy(
    monkeypatch,
):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response(
        anonymous={
            "is_proxy": True,
            "is_vpn": True,
            "is_tor": False,
            "is_relay": False,
        }
    )

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["is_vpn"] is True
    assert result["is_proxy"] is True
    assert result["is_tor"] is False
    assert result["is_relay"] is False
    assert result["privacy_signals_available"] is True


def test_analyze_ip_detects_tor_and_relay(monkeypatch):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response(
        anonymous={
            "is_proxy": False,
            "is_vpn": False,
            "is_tor": True,
            "is_relay": True,
        }
    )

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["is_tor"] is True
    assert result["is_relay"] is True
    assert result["is_anonymous"] is True


def test_analyze_ip_detects_country_mismatch_by_country_code(
    monkeypatch,
):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response()

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip(
        "8.8.8.8",
        user_country="KE",
    )

    assert result["country_mismatch"] is True
    assert result["risk_flag"] == "low"


def test_analyze_ip_matches_country_name_case_insensitively(
    monkeypatch,
):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response()

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip(
        "8.8.8.8",
        user_country="united states",
    )

    assert result["country_mismatch"] is False


def test_analyze_ip_sanitizes_malformed_provider_fields(monkeypatch):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response()
    data["geo"].update(
        {
            "country": 123,
            "country_code": [],
            "region": "   ",
            "city": None,
        }
    )
    data["as"].update(
        {
            "asn": 15169,
            "name": {"unexpected": "object"},
            "type": ["residential"],
        }
    )

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["status"] == "ok"
    assert result["country"] is None
    assert result["country_code"] is None
    assert result["region"] is None
    assert result["city"] is None
    assert result["asn"] is None
    assert result["isp"] is None
    assert result["organization"] is None
    assert result["network_type"] is None
    assert result["is_residential"] is None


def test_analyze_ip_ignores_non_string_user_country(monkeypatch):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response()
    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip(
        "8.8.8.8",
        user_country=["KE"],
    )

    assert result["status"] == "ok"
    assert result["country_mismatch"] is False


def test_analyze_ip_rejects_invalid_ip_without_provider_request(
    monkeypatch,
):
    configure_ipinfo(monkeypatch)

    def unexpected_request(*args, **kwargs):
        raise AssertionError("Provider must not be called for invalid IPs")

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        unexpected_request,
    )

    result = ip_service.analyze_ip("not-an-ip")

    assert result["status"] == "invalid"
    assert result["error_code"] == "invalid_ip"
    assert result["risk_flag"] == "unknown"


def test_analyze_ip_rejects_non_public_ip_without_provider_request(
    monkeypatch,
):
    configure_ipinfo(monkeypatch)

    def unexpected_request(*args, **kwargs):
        raise AssertionError(
            "Provider must not be called for non-public IPs"
        )

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        unexpected_request,
    )

    for ip in ("127.0.0.1", "10.0.0.1", "192.168.1.1", "224.0.0.1", "ff02::1"):
        result = ip_service.analyze_ip(ip)

        assert result["status"] == "not_public"
        assert result["error_code"] == "non_public_ip"
        assert result["risk_flag"] == "unknown"


def test_analyze_ip_handles_missing_provider_token(monkeypatch):
    monkeypatch.setattr(ip_service.config, "IPINFO_TOKEN", None)

    def unexpected_request(*args, **kwargs):
        raise AssertionError("Provider must not be called without a token")

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        unexpected_request,
    )

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["status"] == "unavailable"
    assert result["error_code"] == "provider_not_configured"
    assert result["risk_flag"] == "unknown"


def test_analyze_ip_handles_provider_timeout(monkeypatch):
    configure_ipinfo(monkeypatch)

    def fake_get(*args, **kwargs):
        raise requests.Timeout("simulated timeout")

    monkeypatch.setattr(ip_service.requests, "get", fake_get)

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["status"] == "unavailable"
    assert result["error_code"] == "provider_timeout"
    assert result["risk_flag"] == "unknown"


def test_analyze_ip_handles_provider_rate_limit(monkeypatch):
    configure_ipinfo(monkeypatch)

    def fake_get(*args, **kwargs):
        return FakeResponse(status_code=429)

    monkeypatch.setattr(ip_service.requests, "get", fake_get)

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["status"] == "unavailable"
    assert result["error_code"] == "provider_rate_limited"
    assert result["risk_flag"] == "unknown"


def test_analyze_ip_handles_provider_auth_error(monkeypatch):
    configure_ipinfo(monkeypatch)

    def fake_get(*args, **kwargs):
        return FakeResponse(status_code=401)

    monkeypatch.setattr(ip_service.requests, "get", fake_get)

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["status"] == "unavailable"
    assert result["error_code"] == "provider_auth_error"
    assert result["risk_flag"] == "unknown"


def test_analyze_ip_handles_other_http_errors(monkeypatch):
    configure_ipinfo(monkeypatch)

    def fake_get(*args, **kwargs):
        return FakeResponse(status_code=500)

    monkeypatch.setattr(ip_service.requests, "get", fake_get)

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["status"] == "unavailable"
    assert result["error_code"] == "provider_http_error"
    assert result["risk_flag"] == "unknown"


def test_analyze_ip_handles_invalid_json(monkeypatch):
    configure_ipinfo(monkeypatch)

    def fake_get(*args, **kwargs):
        return FakeResponse(json_error=requests.exceptions.JSONDecodeError("invalid JSON", "x", 0))

    monkeypatch.setattr(ip_service.requests, "get", fake_get)

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["status"] == "unavailable"
    assert result["error_code"] == "provider_invalid_response"
    assert result["risk_flag"] == "unknown"


def test_analyze_ip_handles_non_object_provider_response(monkeypatch):
    configure_ipinfo(monkeypatch)

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(["unexpected"]),
    )

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["status"] == "unavailable"
    assert result["error_code"] == "provider_invalid_response"


def test_analyze_ip_marks_missing_privacy_signals_unavailable(
    monkeypatch,
):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response(anonymous={"is_vpn": True})

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["status"] == "ok"
    assert result["is_vpn"] is True
    assert result["privacy_signals_available"] is False


def test_analyze_ip_does_not_infer_residential_from_network_type(
    monkeypatch,
):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response(network_type="residential")

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["network_type"] == "residential"
    assert result["is_residential"] is None


def test_analyze_ip_does_not_infer_residential_from_mixed_case_network_type(
    monkeypatch,
):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response(network_type="Residential")
    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["network_type"] == "Residential"
    assert result["is_residential"] is None


def test_analyze_ip_does_not_assume_unknown_network_is_residential(
    monkeypatch,
):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response(
        network_type="isp",
        is_hosting=False,
    )

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["is_residential"] is None


def test_analyze_ip_marks_hosting_network_as_not_residential(
    monkeypatch,
):
    configure_ipinfo(monkeypatch)

    data = make_ipinfo_response(
        network_type="hosting",
        is_hosting=True,
    )

    monkeypatch.setattr(
        ip_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(data),
    )

    result = ip_service.analyze_ip("8.8.8.8")

    assert result["is_hosting"] is True
    assert result["is_residential"] is False
    assert result["risk_flag"] == "medium"
