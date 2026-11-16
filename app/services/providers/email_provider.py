from typing import Any

from app.services.email_service import analyze_email
from app.services.providers.base import (
    IntelligenceProvider,
    ProviderCategory,
)


class LocalEmailProvider(IntelligenceProvider):
    """Adapter for local email format, disposable-domain, and MX intelligence."""

    @property
    def name(self) -> str:
        return "local_email"

    @property
    def category(self) -> ProviderCategory:
        return ProviderCategory.EMAIL

    @property
    def is_configured(self) -> bool:
        return True

    def analyze(self, value: str, **context: Any) -> dict[str, Any]:
        return analyze_email(value)
