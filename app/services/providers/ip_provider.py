from typing import Any

from app.services.ip_service import analyze_ip
from app.services.providers.base import (
    IntelligenceProvider,
    ProviderCategory,
)


class IPInfoProvider(IntelligenceProvider):
    """Adapter for IPinfo Plus network and privacy intelligence."""

    @property
    def name(self) -> str:
        return "ipinfo"

    @property
    def category(self) -> ProviderCategory:
        return ProviderCategory.IP

    @property
    def is_configured(self) -> bool:
        # The adapter is executable even without upstream credentials.
        # analyze_ip() handles missing IPinfo credentials and returns
        # a normalized provider_not_configured result without making
        # an external request.
        return True

    def analyze(self, value: str, **context: Any) -> dict[str, Any]:
        return analyze_ip(
            value,
            user_country=context.get("user_country"),
        )
