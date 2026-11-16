from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ProviderCategory(str, Enum):
    EMAIL = "email"
    IP = "ip"
    PHONE = "phone"


class ProviderStatus(str, Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"
    INVALID_INPUT = "invalid_input"
    ERROR = "error"


@dataclass(frozen=True)
class ProviderExecutionResult:
    provider_name: str
    category: ProviderCategory
    status: ProviderStatus
    data: dict[str, Any] | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_name or not self.provider_name.strip():
            raise ValueError("provider_name must not be empty")

        if not isinstance(self.category, ProviderCategory):
            raise TypeError("category must be a ProviderCategory")

        if not isinstance(self.status, ProviderStatus):
            raise TypeError("status must be a ProviderStatus")

        if self.data is not None and not isinstance(self.data, dict):
            raise TypeError("data must be a dictionary or None")

        if self.error_code is not None and (
            not isinstance(self.error_code, str) or not self.error_code.strip()
        ):
            raise ValueError("error_code must be a non-empty string or None")

        if self.status is ProviderStatus.SUCCESS and self.data is None:
            raise ValueError("successful execution must include provider data")


class IntelligenceProvider(ABC):
    """Contract implemented by an intelligence provider adapter."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable provider identifier."""

    @property
    @abstractmethod
    def category(self) -> ProviderCategory:
        """Return the intelligence category handled by this provider."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return whether the adapter can execute safely with local configuration.

        Upstream configuration may instead be reported through the
        provider's normalized analysis result.
        """

    @abstractmethod
    def analyze(self, value: str, **context: Any) -> dict[str, Any]:
        """Analyze one input and return normalized intelligence data."""
