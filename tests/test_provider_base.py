from typing import Any

import pytest

from app.services.providers.base import (
    IntelligenceProvider,
    ProviderCategory,
    ProviderExecutionResult,
    ProviderStatus,
)


class FakeProvider(IntelligenceProvider):
    @property
    def name(self) -> str:
        return "test_provider"

    @property
    def category(self) -> ProviderCategory:
        return ProviderCategory.EMAIL

    @property
    def is_configured(self) -> bool:
        return True

    def analyze(self, value: str, **context: Any) -> dict[str, Any]:
        return {"value": value}


def test_provider_category_values():
    assert ProviderCategory.EMAIL.value == "email"
    assert ProviderCategory.IP.value == "ip"
    assert ProviderCategory.PHONE.value == "phone"


def test_provider_status_values():
    assert ProviderStatus.SUCCESS.value == "success"
    assert ProviderStatus.SKIPPED.value == "skipped"
    assert ProviderStatus.TIMEOUT.value == "timeout"
    assert ProviderStatus.UNAVAILABLE.value == "unavailable"
    assert ProviderStatus.NOT_CONFIGURED.value == "not_configured"
    assert ProviderStatus.INVALID_INPUT.value == "invalid_input"
    assert ProviderStatus.ERROR.value == "error"


def test_provider_execution_result_accepts_success():
    result = ProviderExecutionResult(
        provider_name="test_provider",
        category=ProviderCategory.EMAIL,
        status=ProviderStatus.SUCCESS,
        data={"valid_format": True},
    )

    assert result.provider_name == "test_provider"
    assert result.category is ProviderCategory.EMAIL
    assert result.status is ProviderStatus.SUCCESS
    assert result.data == {"valid_format": True}
    assert result.error_code is None


@pytest.mark.parametrize(
    "status",
    [
        ProviderStatus.SKIPPED,
        ProviderStatus.TIMEOUT,
        ProviderStatus.UNAVAILABLE,
        ProviderStatus.NOT_CONFIGURED,
        ProviderStatus.INVALID_INPUT,
        ProviderStatus.ERROR,
    ],
)
def test_provider_execution_result_accepts_non_success_statuses(status):
    result = ProviderExecutionResult(
        provider_name="test_provider",
        category=ProviderCategory.IP,
        status=status,
        error_code="provider_unavailable",
    )

    assert result.status is status
    assert result.data is None
    assert result.error_code == "provider_unavailable"


def test_provider_execution_result_rejects_empty_provider_name():
    with pytest.raises(ValueError, match="provider_name"):
        ProviderExecutionResult(
            provider_name=" ",
            category=ProviderCategory.EMAIL,
            status=ProviderStatus.ERROR,
        )


def test_provider_execution_result_rejects_success_without_data():
    with pytest.raises(ValueError, match="successful execution"):
        ProviderExecutionResult(
            provider_name="test_provider",
            category=ProviderCategory.EMAIL,
            status=ProviderStatus.SUCCESS,
        )


def test_provider_execution_result_rejects_invalid_data_type():
    with pytest.raises(TypeError, match="data"):
        ProviderExecutionResult(
            provider_name="test_provider",
            category=ProviderCategory.EMAIL,
            status=ProviderStatus.SUCCESS,
            data="invalid",
        )


def test_provider_execution_result_is_immutable():
    result = ProviderExecutionResult(
        provider_name="test_provider",
        category=ProviderCategory.PHONE,
        status=ProviderStatus.SUCCESS,
        data={"phone_valid": True},
    )

    with pytest.raises(AttributeError):
        result.status = ProviderStatus.ERROR


def test_provider_interface_implementation():
    provider = FakeProvider()

    assert provider.name == "test_provider"
    assert provider.category is ProviderCategory.EMAIL
    assert provider.is_configured is True
    assert provider.analyze("person@example.com") == {
        "value": "person@example.com"
    }


def test_incomplete_provider_cannot_be_instantiated():
    class IncompleteProvider(IntelligenceProvider):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider()
