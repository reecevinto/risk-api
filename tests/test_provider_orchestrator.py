import pytest

from app.services.provider_orchestrator import (
    ProviderOrchestrator,
    create_default_registry,
)
from app.services.providers.base import (
    IntelligenceProvider,
    ProviderCategory,
    ProviderStatus,
)
from app.services.providers.registry import ProviderRegistry


class FakeProvider(IntelligenceProvider):
    def __init__(
        self,
        name: str,
        category: ProviderCategory,
        result: dict | None = None,
        *,
        configured: bool = True,
        exception: Exception | None = None,
    ) -> None:
        self._name = name
        self._category = category
        self._result = result if result is not None else {"result": "ok"}
        self._configured = configured
        self._exception = exception
        self.calls: list[tuple[str, dict]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> ProviderCategory:
        return self._category

    @property
    def is_configured(self) -> bool:
        return self._configured

    def analyze(self, value: str, **context) -> dict:
        self.calls.append((value, context))

        if self._exception is not None:
            raise self._exception

        return self._result


class NonDictionaryProvider(FakeProvider):
    def analyze(self, value: str, **context):
        self.calls.append((value, context))
        return "invalid provider response"


def test_default_registry_registers_existing_providers():
    registry = create_default_registry()

    assert len(registry) == 3
    assert registry.get_provider("local_email") is not None
    assert registry.get_provider("local_phone") is not None
    assert registry.get_provider("ipinfo") is not None

    assert registry.get_providers(ProviderCategory.EMAIL)[0].name == "local_email"
    assert registry.get_providers(ProviderCategory.PHONE)[0].name == "local_phone"
    assert registry.get_providers(ProviderCategory.IP)[0].name == "ipinfo"


def test_explicitly_injected_empty_registry_is_preserved():
    registry = ProviderRegistry()
    orchestrator = ProviderOrchestrator(registry)

    assert orchestrator.registry is registry
    assert len(orchestrator.registry) == 0

    result = orchestrator.analyze_inputs(email="user@example.com")

    assert result.data[ProviderCategory.EMAIL] is None
    assert result.executions == ()


def test_missing_inputs_are_not_executed():
    provider = FakeProvider("email_test", ProviderCategory.EMAIL)
    registry = ProviderRegistry()
    registry.register(provider)

    result = ProviderOrchestrator(registry).analyze_inputs()

    assert provider.calls == []
    assert result.executions == ()
    assert result.data == {
        ProviderCategory.EMAIL: None,
        ProviderCategory.PHONE: None,
        ProviderCategory.IP: None,
    }


def test_each_supplied_category_is_executed_once():
    email = FakeProvider(
        "email_test",
        ProviderCategory.EMAIL,
        {"valid_format": True},
    )
    phone = FakeProvider(
        "phone_test",
        ProviderCategory.PHONE,
        {"phone_valid": True},
    )
    ip = FakeProvider(
        "ip_test",
        ProviderCategory.IP,
        {"status": "ok", "country": "KE"},
    )

    registry = ProviderRegistry()
    registry.register(email)
    registry.register(phone)
    registry.register(ip)

    result = ProviderOrchestrator(registry).analyze_inputs(
        email="user@example.com",
        phone="+254700000000",
        ip="8.8.8.8",
    )

    assert len(email.calls) == 1
    assert len(phone.calls) == 1
    assert len(ip.calls) == 1

    assert result.data[ProviderCategory.EMAIL] == {"valid_format": True}
    assert result.data[ProviderCategory.PHONE] == {"phone_valid": True}
    assert result.data[ProviderCategory.IP] == {
        "status": "ok",
        "country": "KE",
    }

    assert [item.provider_name for item in result.executions] == [
        "email_test",
        "phone_test",
        "ip_test",
    ]

    assert all(
        item.status is ProviderStatus.SUCCESS
        for item in result.executions
    )


@pytest.mark.parametrize(
    ("category", "value"),
    [
        (ProviderCategory.EMAIL, "invalid-email"),
        (ProviderCategory.PHONE, "invalid-phone"),
    ],
)
def test_local_analysis_results_are_successful_executions(
    category,
    value,
):
    provider = FakeProvider(
        "local_test",
        category,
        {"valid": False, "risk_flag": "high"},
    )
    registry = ProviderRegistry()
    registry.register(provider)

    result = ProviderOrchestrator(registry).analyze_inputs(
        **{
            "email" if category is ProviderCategory.EMAIL else "phone": value
        }
    )

    assert len(provider.calls) == 1
    assert result.executions[0].status is ProviderStatus.SUCCESS
    assert result.data[category] == {
        "valid": False,
        "risk_flag": "high",
    }


@pytest.mark.parametrize(
    ("provider_data", "expected_status", "expected_error"),
    [
        ({"status": "ok"}, ProviderStatus.SUCCESS, None),
        (
            {"status": "invalid", "error_code": "invalid_ip"},
            ProviderStatus.INVALID_INPUT,
            "invalid_ip",
        ),
        (
            {"status": "not_public", "error_code": "non_public_ip"},
            ProviderStatus.INVALID_INPUT,
            "non_public_ip",
        ),
        (
            {
                "status": "unavailable",
                "error_code": "provider_not_configured",
            },
            ProviderStatus.NOT_CONFIGURED,
            "provider_not_configured",
        ),
        (
            {"status": "unavailable", "error_code": "provider_timeout"},
            ProviderStatus.TIMEOUT,
            "provider_timeout",
        ),
        (
            {
                "status": "unavailable",
                "error_code": "provider_rate_limited",
            },
            ProviderStatus.UNAVAILABLE,
            "provider_rate_limited",
        ),
        (
            {"status": "unexpected"},
            ProviderStatus.ERROR,
            "invalid_provider_response",
        ),
    ],
)
def test_ip_execution_status_mapping(
    provider_data,
    expected_status,
    expected_error,
):
    provider = FakeProvider(
        "ip_test",
        ProviderCategory.IP,
        provider_data,
    )
    registry = ProviderRegistry()
    registry.register(provider)

    result = ProviderOrchestrator(registry).analyze_inputs(
        ip="8.8.8.8"
    )

    execution = result.executions[0]

    assert execution.status is expected_status
    assert execution.error_code == expected_error


def test_unrecognized_ip_status_is_not_exposed_to_risk_scoring():
    provider_data = {
        "status": "unexpected",
        "risk_flag": "high",
        "is_vpn": True,
    }
    provider = FakeProvider(
        "ip_test",
        ProviderCategory.IP,
        provider_data,
    )
    registry = ProviderRegistry()
    registry.register(provider)

    result = ProviderOrchestrator(registry).analyze_inputs(
        ip="8.8.8.8"
    )

    execution = result.executions[0]

    assert execution.status is ProviderStatus.ERROR
    assert execution.error_code == "invalid_provider_response"
    assert execution.data is None
    assert result.data[ProviderCategory.IP] is None


@pytest.mark.parametrize(
    "provider_data",
    [
        {"status": "invalid", "error_code": "invalid_ip"},
        {"status": "not_public", "error_code": "non_public_ip"},
        {
            "status": "unavailable",
            "error_code": "provider_not_configured",
        },
        {"status": "unavailable", "error_code": "provider_timeout"},
        {
            "status": "unavailable",
            "error_code": "provider_rate_limited",
        },
    ],
)
def test_non_successful_ip_execution_preserves_original_intelligence_data(
    provider_data,
):
    provider = FakeProvider(
        "ip_test",
        ProviderCategory.IP,
        provider_data,
    )
    registry = ProviderRegistry()
    registry.register(provider)

    result = ProviderOrchestrator(registry).analyze_inputs(
        ip="8.8.8.8"
    )

    execution = result.executions[0]

    assert execution.status is not ProviderStatus.SUCCESS
    assert result.data[ProviderCategory.IP] is provider_data
    assert execution.data is provider_data


def test_disabled_provider_is_skipped_without_execution():
    provider = FakeProvider("email_test", ProviderCategory.EMAIL)
    registry = ProviderRegistry()
    registry.register(provider, enabled=False)

    result = ProviderOrchestrator(registry).analyze_inputs(
        email="user@example.com"
    )

    assert provider.calls == []
    assert result.data[ProviderCategory.EMAIL] is None
    assert len(result.executions) == 1
    assert result.executions[0].status is ProviderStatus.SKIPPED
    assert result.executions[0].error_code == "provider_disabled"


def test_unconfigured_provider_is_not_executed():
    provider = FakeProvider(
        "email_test",
        ProviderCategory.EMAIL,
        configured=False,
    )
    registry = ProviderRegistry()
    registry.register(provider)

    result = ProviderOrchestrator(registry).analyze_inputs(
        email="user@example.com"
    )

    assert provider.calls == []
    assert result.data[ProviderCategory.EMAIL] is None
    assert result.executions[0].status is ProviderStatus.NOT_CONFIGURED
    assert result.executions[0].error_code == "provider_not_configured"


def test_multiple_enabled_providers_are_rejected_as_ambiguous():
    first = FakeProvider("email_first", ProviderCategory.EMAIL)
    second = FakeProvider("email_second", ProviderCategory.EMAIL)

    registry = ProviderRegistry()
    registry.register(first)
    registry.register(second)

    result = ProviderOrchestrator(registry).analyze_inputs(
        email="user@example.com"
    )

    assert first.calls == []
    assert second.calls == []
    assert result.data[ProviderCategory.EMAIL] is None
    assert len(result.executions) == 2

    assert all(
        item.status is ProviderStatus.ERROR
        for item in result.executions
    )
    assert all(
        item.error_code == "ambiguous_provider_configuration"
        for item in result.executions
    )


def test_provider_exception_is_isolated_from_other_categories():
    failing_email = FakeProvider(
        "email_test",
        ProviderCategory.EMAIL,
        exception=RuntimeError("sensitive internal provider details"),
    )
    working_phone = FakeProvider(
        "phone_test",
        ProviderCategory.PHONE,
        {"phone_valid": True},
    )

    registry = ProviderRegistry()
    registry.register(failing_email)
    registry.register(working_phone)

    result = ProviderOrchestrator(registry).analyze_inputs(
        email="user@example.com",
        phone="+254700000000",
    )

    assert len(failing_email.calls) == 1
    assert len(working_phone.calls) == 1

    assert result.data[ProviderCategory.EMAIL] is None
    assert result.data[ProviderCategory.PHONE] == {"phone_valid": True}

    email_execution = result.executions[0]

    assert email_execution.status is ProviderStatus.ERROR
    assert email_execution.error_code == "provider_execution_failed"
    assert "sensitive" not in str(email_execution)


def test_non_dictionary_provider_response_is_sanitized():
    provider = NonDictionaryProvider(
        "email_test",
        ProviderCategory.EMAIL,
    )
    registry = ProviderRegistry()
    registry.register(provider)

    result = ProviderOrchestrator(registry).analyze_inputs(
        email="user@example.com"
    )

    assert len(provider.calls) == 1
    assert result.data[ProviderCategory.EMAIL] is None
    assert result.executions[0].status is ProviderStatus.ERROR
    assert result.executions[0].error_code == "provider_execution_failed"
    assert "invalid provider response" not in str(result.executions[0])


def test_ip_provider_receives_user_country_context():
    provider = FakeProvider(
        "ip_test",
        ProviderCategory.IP,
        {"status": "ok"},
    )
    registry = ProviderRegistry()
    registry.register(provider)

    ProviderOrchestrator(registry).analyze_inputs(
        ip="8.8.8.8",
        user_country="KE",
    )

    assert provider.calls == [
        ("8.8.8.8", {"user_country": "KE"})
    ]


def test_non_ip_providers_do_not_receive_ip_context():
    provider = FakeProvider(
        "email_test",
        ProviderCategory.EMAIL,
        {"valid_format": True},
    )
    registry = ProviderRegistry()
    registry.register(provider)

    ProviderOrchestrator(registry).analyze_inputs(
        email="user@example.com",
        user_country="KE",
    )

    assert provider.calls == [
        ("user@example.com", {})
    ]


def test_orchestration_result_preserves_provider_execution_order():
    registry = ProviderRegistry()

    registry.register(
        FakeProvider("ip_test", ProviderCategory.IP, {"status": "ok"})
    )
    registry.register(
        FakeProvider("phone_test", ProviderCategory.PHONE, {"valid": True})
    )
    registry.register(
        FakeProvider("email_test", ProviderCategory.EMAIL, {"valid": True})
    )

    result = ProviderOrchestrator(registry).analyze_inputs(
        email="user@example.com",
        phone="+254700000000",
        ip="8.8.8.8",
    )

    assert [item.category for item in result.executions] == [
        ProviderCategory.EMAIL,
        ProviderCategory.PHONE,
        ProviderCategory.IP,
    ]


def test_empty_inputs_are_skipped_without_provider_execution():
    email = FakeProvider("email_test", ProviderCategory.EMAIL)
    phone = FakeProvider("phone_test", ProviderCategory.PHONE)
    ip = FakeProvider("ip_test", ProviderCategory.IP)

    registry = ProviderRegistry()
    registry.register(email)
    registry.register(phone)
    registry.register(ip)

    result = ProviderOrchestrator(registry).analyze_inputs(
        email="",
        phone="",
        ip="",
    )

    assert email.calls == []
    assert phone.calls == []
    assert ip.calls == []

    assert result.data == {
        ProviderCategory.EMAIL: None,
        ProviderCategory.PHONE: None,
        ProviderCategory.IP: None,
    }
    assert result.executions == ()


def test_configuration_check_exception_is_isolated_from_other_categories():
    class ConfigurationErrorProvider(FakeProvider):
        @property
        def is_configured(self) -> bool:
            raise RuntimeError("sensitive configuration details")

    failing_email = ConfigurationErrorProvider(
        "email_test",
        ProviderCategory.EMAIL,
    )
    working_phone = FakeProvider(
        "phone_test",
        ProviderCategory.PHONE,
        {"phone_valid": True},
    )

    registry = ProviderRegistry()
    registry.register(failing_email)
    registry.register(working_phone)

    result = ProviderOrchestrator(registry).analyze_inputs(
        email="user@example.com",
        phone="+254700000000",
    )

    assert failing_email.calls == []
    assert len(working_phone.calls) == 1

    assert result.data[ProviderCategory.EMAIL] is None
    assert result.data[ProviderCategory.PHONE] == {"phone_valid": True}

    email_execution = result.executions[0]

    assert email_execution.status is ProviderStatus.ERROR
    assert email_execution.error_code == "provider_configuration_check_failed"
    assert "sensitive" not in str(email_execution)
