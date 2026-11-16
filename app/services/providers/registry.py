from app.services.providers.base import (
    IntelligenceProvider,
    ProviderCategory,
)


class ProviderRegistry:
    """Register and retrieve intelligence providers."""

    def __init__(self) -> None:
        self._providers: dict[str, IntelligenceProvider] = {}
        self._enabled: dict[str, bool] = {}

    def register(
        self,
        provider: IntelligenceProvider,
        *,
        enabled: bool = True,
    ) -> None:
        if not isinstance(provider, IntelligenceProvider):
            raise TypeError("provider must implement IntelligenceProvider")

        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a boolean")

        name = provider.name

        if not isinstance(name, str) or not name.strip():
            raise ValueError("provider name must not be empty")

        if name in self._providers:
            raise ValueError(f"provider already registered: {name}")

        if not isinstance(provider.category, ProviderCategory):
            raise TypeError("provider category must be a ProviderCategory")

        self._providers[name] = provider
        self._enabled[name] = enabled

    def get_provider(self, name: str) -> IntelligenceProvider | None:
        return self._providers.get(name)

    def get_providers(
        self,
        category: ProviderCategory,
        *,
        enabled_only: bool = True,
    ) -> list[IntelligenceProvider]:
        if not isinstance(category, ProviderCategory):
            raise TypeError("category must be a ProviderCategory")

        if not isinstance(enabled_only, bool):
            raise TypeError("enabled_only must be a boolean")

        return [
            provider
            for name, provider in self._providers.items()
            if provider.category is category
            and (not enabled_only or self._enabled[name])
        ]

    def is_enabled(self, name: str) -> bool:
        if name not in self._providers:
            raise KeyError(f"provider not registered: {name}")

        return self._enabled[name]

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name not in self._providers:
            raise KeyError(f"provider not registered: {name}")

        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a boolean")

        self._enabled[name] = enabled

    def unregister(self, name: str) -> None:
        if name not in self._providers:
            raise KeyError(f"provider not registered: {name}")

        del self._providers[name]
        del self._enabled[name]

    def __len__(self) -> int:
        return len(self._providers)
