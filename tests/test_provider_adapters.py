from unittest.mock import Mock

from app.services.providers import email_provider, ip_provider, phone_provider
from app.services.providers.base import ProviderCategory
from app.services.providers.email_provider import LocalEmailProvider
from app.services.providers.ip_provider import IPInfoProvider
from app.services.providers.phone_provider import LocalPhoneProvider


class TestLocalEmailProvider:
    def test_provider_metadata(self):
        provider = LocalEmailProvider()

        assert provider.name == "local_email"
        assert provider.category is ProviderCategory.EMAIL
        assert provider.is_configured is True

    def test_analyze_delegates_once_and_preserves_result(self, monkeypatch):
        expected = {
            "valid_format": True,
            "domain": "example.com",
            "mx_records": ["mx.example.com"],
            "mx_status": "present",
            "disposable": False,
            "risk_flag": "low",
        }
        analyze_mock = Mock(return_value=expected)
        monkeypatch.setattr(email_provider, "analyze_email", analyze_mock)

        provider = LocalEmailProvider()
        result = provider.analyze("user@example.com")

        analyze_mock.assert_called_once_with("user@example.com")
        assert result is expected


class TestLocalPhoneProvider:
    def test_provider_metadata(self):
        provider = LocalPhoneProvider()

        assert provider.name == "local_phone"
        assert provider.category is ProviderCategory.PHONE
        assert provider.is_configured is True

    def test_analyze_delegates_once_and_preserves_result(self, monkeypatch):
        expected = {
            "phone_valid": True,
            "number_possible": True,
            "country": "KE",
            "carrier": "Example Carrier",
            "carrier_source": "phonenumbers_metadata",
            "line_type": "mobile",
            "number_type": "mobile",
            "is_african_region": True,
        }
        analyze_mock = Mock(return_value=expected)
        monkeypatch.setattr(phone_provider, "analyze_phone", analyze_mock)

        provider = LocalPhoneProvider()
        result = provider.analyze("+254712345678")

        analyze_mock.assert_called_once_with("+254712345678")
        assert result is expected


class TestIPInfoProvider:
    def test_provider_metadata(self):
        provider = IPInfoProvider()

        assert provider.name == "ipinfo"
        assert provider.category is ProviderCategory.IP
        assert provider.is_configured is True

    def test_analyze_forwards_user_country_and_preserves_result(
        self,
        monkeypatch,
    ):
        expected = {
            "status": "ok",
            "ip": "8.8.8.8",
            "country": "US",
            "risk_flag": "low",
        }
        analyze_mock = Mock(return_value=expected)
        monkeypatch.setattr(ip_provider, "analyze_ip", analyze_mock)

        provider = IPInfoProvider()
        result = provider.analyze("8.8.8.8", user_country="KE")

        analyze_mock.assert_called_once_with(
            "8.8.8.8",
            user_country="KE",
        )
        assert result is expected

    def test_analyze_defaults_user_country_to_none(self, monkeypatch):
        expected = {"status": "ok", "ip": "8.8.8.8"}
        analyze_mock = Mock(return_value=expected)
        monkeypatch.setattr(ip_provider, "analyze_ip", analyze_mock)

        provider = IPInfoProvider()
        result = provider.analyze("8.8.8.8")

        analyze_mock.assert_called_once_with(
            "8.8.8.8",
            user_country=None,
        )
        assert result is expected
