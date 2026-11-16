from typing import Any

import pytest

from app.services.providers.base import (
    IntelligenceProvider,
    ProviderCategory,
)
from app.services.providers.registry import ProviderRegistry


class FakeProvider(IntelligenceProvider):
    def __init__(
        self,
        name: str,
        category: ProviderCategory,
        configured: bool = True,
    ):
        self._name = name
        self._category = category
        self._configured = configured

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> ProviderCategory:
        return self._category

    @property
    def is_configured(self) -> bool:
        return self._configured

    def analyze(self, value: str, **context: Any) -> dict[str, Any]:
        return {"value": value}


def test_register_and_retrieve_provider():
    registry = ProviderRegistry()
    provider = FakeProvider("email_primary", ProviderCategory.EMAIL)

    registry.register(provider)

    assert len(registry) == 1
    assert registry.get_provider("email_primary") is provider
    assert registry.is_enabled("email_primary") is True


def test_registry_supports_multiple_providers_per_category():
    registry = ProviderRegistry()
    first = FakeProvider("email_primary", ProviderCategory.EMAIL)
    second = FakeProvider("email_secondary", ProviderCategory.EMAIL)

    registry.register(first)
    registry.register(second)

    providers = registry.get_providers(ProviderCategory.EMAIL)

    assert providers == [first, second]


def test_registry_filters_by_category():
    registry = ProviderRegistry()
    email = FakeProvider("email_primary", ProviderCategory.EMAIL)
    ip = FakeProvider("ip_primary", ProviderCategory.IP)

    registry.register(email)
    registry.register(ip)

    assert registry.get_providers(ProviderCategory.EMAIL) == [email]
    assert registry.get_providers(ProviderCategory.IP) == [ip]
    assert registry.get_providers(ProviderCategory.PHONE) == []


def test_disabled_provider_is_not_returned_by_default():
    registry = ProviderRegistry()
    provider = FakeProvider("email_primary", ProviderCategory.EMAIL)

    registry.register(provider, enabled=False)

    assert registry.get_providers(ProviderCategory.EMAIL) == []
    assert registry.get_providers(
        ProviderCategory.EMAIL,
        enabled_only=False,
    ) == [provider]


def test_enable_and_disable_provider():
    registry = ProviderRegistry()
    provider = FakeProvider("email_primary", ProviderCategory.EMAIL)

    registry.register(provider, enabled=False)

    registry.set_enabled("email_primary", True)

    assert registry.is_enabled("email_primary") is True
    assert registry.get_providers(ProviderCategory.EMAIL) == [provider]

    registry.set_enabled("email_primary", False)

    assert registry.is_enabled("email_primary") is False
    assert registry.get_providers(ProviderCategory.EMAIL) == []


def test_unconfigured_provider_remains_registered_and_visible():
    registry = ProviderRegistry()
    provider = FakeProvider(
        "ip_primary",
        ProviderCategory.IP,
        configured=False,
    )

    registry.register(provider)

    assert registry.get_providers(ProviderCategory.IP) == [provider]
    assert provider.is_configured is False


def test_duplicate_provider_name_is_rejected():
    registry = ProviderRegistry()
    first = FakeProvider("email_primary", ProviderCategory.EMAIL)
    second = FakeProvider("email_primary", ProviderCategory.IP)

    registry.register(first)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(second)


def test_invalid_provider_is_rejected():
    registry = ProviderRegistry()

    with pytest.raises(TypeError, match="IntelligenceProvider"):
        registry.register(object())


def test_invalid_enabled_value_is_rejected():
    registry = ProviderRegistry()
    provider = FakeProvider("email_primary", ProviderCategory.EMAIL)

    with pytest.raises(TypeError, match="enabled"):
        registry.register(provider, enabled=1)


def test_invalid_category_query_is_rejected():
    registry = ProviderRegistry()

    with pytest.raises(TypeError, match="ProviderCategory"):
        registry.get_providers("email")


def test_unknown_provider_lookup_returns_none():
    registry = ProviderRegistry()

    assert registry.get_provider("missing") is None


def test_unknown_provider_enablement_raises_key_error():
    registry = ProviderRegistry()

    with pytest.raises(KeyError, match="not registered"):
        registry.is_enabled("missing")


def test_unknown_provider_cannot_be_enabled():
    registry = ProviderRegistry()

    with pytest.raises(KeyError, match="not registered"):
        registry.set_enabled("missing", True)


def test_unregister_removes_provider_and_enablement():
    registry = ProviderRegistry()
    provider = FakeProvider("email_primary", ProviderCategory.EMAIL)

    registry.register(provider)
    registry.unregister("email_primary")

    assert len(registry) == 0
    assert registry.get_provider("email_primary") is None
    assert registry.get_providers(ProviderCategory.EMAIL) == []


def test_unregister_unknown_provider_raises_key_error():
    registry = ProviderRegistry()

    with pytest.raises(KeyError, match="not registered"):
        registry.unregister("missing")


def test_registry_preserves_registration_order():
    registry = ProviderRegistry()
    first = FakeProvider("email_first", ProviderCategory.EMAIL)
    second = FakeProvider("email_second", ProviderCategory.EMAIL)
    third = FakeProvider("email_third", ProviderCategory.EMAIL)

    registry.register(first)
    registry.register(second)
    registry.register(third)

    assert registry.get_providers(ProviderCategory.EMAIL) == [
        first,
        second,
        third,
    ]
