import dns.resolver
import pytest

from app.services.email_service import (
    DISPOSABLE_DOMAINS,
    analyze_email,
)


class FakeMXAnswer:
    def __bool__(self):
        return True


def test_valid_email_normalizes_domain_and_detects_mx(monkeypatch):
    def fake_resolve(domain, record_type, lifetime):
        assert domain == "example.com"
        assert record_type == "MX"
        assert lifetime > 0
        return FakeMXAnswer()

    monkeypatch.setattr(
        "app.services.email_service.dns.resolver.resolve",
        fake_resolve,
    )

    result = analyze_email("  Person@EXAMPLE.COM  ")

    assert result["valid_format"] is True
    assert result["domain"] == "example.com"
    assert result["mx_records"] is True
    assert result["mx_status"] == "present"
    assert result["disposable"] is False
    assert result["risk_flag"] == "low"


@pytest.mark.parametrize(
    "email",
    [
        "",
        "   ",
        "not-an-email",
        "missing-at.example.com",
        "person@invalid",
        "person@@example.com",
        "person@example..com",
    ],
)
def test_invalid_email_is_rejected_without_dns_lookup(monkeypatch, email):
    def unexpected_resolve(*args, **kwargs):
        pytest.fail("DNS must not be queried for an invalid email")

    monkeypatch.setattr(
        "app.services.email_service.dns.resolver.resolve",
        unexpected_resolve,
    )

    result = analyze_email(email)

    assert result["valid_format"] is False
    assert result["domain"] == ""
    assert result["mx_status"] == "not_checked"
    assert result["risk_flag"] == "high"


@pytest.mark.parametrize(
    "domain",
    sorted(DISPOSABLE_DOMAINS),
)
def test_known_disposable_domains_are_detected(monkeypatch, domain):
    monkeypatch.setattr(
        "app.services.email_service.dns.resolver.resolve",
        lambda *args, **kwargs: FakeMXAnswer(),
    )

    result = analyze_email(f"person@{domain}")

    assert result["valid_format"] is True
    assert result["disposable"] is True
    assert result["risk_flag"] == "high"


def test_subdomain_of_disposable_domain_is_detected(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.dns.resolver.resolve",
        lambda *args, **kwargs: FakeMXAnswer(),
    )

    result = analyze_email("person@mail.mailinator.com")

    assert result["disposable"] is True
    assert result["risk_flag"] == "high"


def test_similar_but_unrelated_domain_is_not_marked_disposable(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.dns.resolver.resolve",
        lambda *args, **kwargs: FakeMXAnswer(),
    )

    result = analyze_email("person@notmailinator.com")

    assert result["disposable"] is False


@pytest.mark.parametrize(
    "exception",
    [
        dns.resolver.NoAnswer(),
        dns.resolver.NXDOMAIN(),
    ],
)
def test_confirmed_missing_mx_is_distinguished(monkeypatch, exception):
    def fake_resolve(*args, **kwargs):
        raise exception

    monkeypatch.setattr(
        "app.services.email_service.dns.resolver.resolve",
        fake_resolve,
    )

    result = analyze_email("person@example.com")

    assert result["valid_format"] is True
    assert result["mx_records"] is False
    assert result["mx_status"] == "missing"
    assert result["risk_flag"] == "medium"


@pytest.mark.parametrize(
    "exception",
    [
        dns.resolver.LifetimeTimeout(),
        dns.resolver.NoNameservers(),
        RuntimeError("simulated resolver failure"),
    ],
)
def test_dns_failures_are_reported_as_unavailable(monkeypatch, exception):
    def fake_resolve(*args, **kwargs):
        raise exception

    monkeypatch.setattr(
        "app.services.email_service.dns.resolver.resolve",
        fake_resolve,
    )

    result = analyze_email("person@example.com")

    assert result["valid_format"] is True
    assert result["mx_records"] is False
    assert result["mx_status"] == "unavailable"
    assert result["risk_flag"] == "low"


def test_dns_error_details_are_not_returned(monkeypatch):
    def fake_resolve(*args, **kwargs):
        raise RuntimeError("internal resolver detail")

    monkeypatch.setattr(
        "app.services.email_service.dns.resolver.resolve",
        fake_resolve,
    )

    result = analyze_email("person@example.com")

    assert "internal resolver detail" not in repr(result)
