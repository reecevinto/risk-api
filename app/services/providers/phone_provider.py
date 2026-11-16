from typing import Any

from app.services.phone_service import analyze_phone
from app.services.providers.base import (
    IntelligenceProvider,
    ProviderCategory,
)


class LocalPhoneProvider(IntelligenceProvider):
    """Adapter for local phone numbering-plan and regional intelligence."""

    @property
    def name(self) -> str:
        return "local_phone"

    @property
    def category(self) -> ProviderCategory:
        return ProviderCategory.PHONE

    @property
    def is_configured(self) -> bool:
        return True

    def analyze(self, value: str, **context: Any) -> dict[str, Any]:
        return analyze_phone(value)
