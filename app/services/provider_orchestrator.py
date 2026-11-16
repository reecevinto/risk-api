from dataclasses import dataclass
from typing import Any

from app.services.providers.base import (
    IntelligenceProvider,
    ProviderCategory,
    ProviderExecutionResult,
    ProviderStatus,
)
from app.services.providers.email_provider import LocalEmailProvider
from app.services.providers.ip_provider import IPInfoProvider
from app.services.providers.phone_provider import LocalPhoneProvider
from app.services.providers.registry import ProviderRegistry


@dataclass(frozen=True)
class OrchestrationResult:
    """Normalized output from intelligence provider execution."""

    data: dict[ProviderCategory, dict[str, Any] | None]
    executions: tuple[ProviderExecutionResult, ...]


def create_default_registry() -> ProviderRegistry:
    """Create the default registry using existing intelligence services."""

    registry = ProviderRegistry()

    registry.register(LocalEmailProvider())
    registry.register(LocalPhoneProvider())
    registry.register(IPInfoProvider())

    return registry


class ProviderOrchestrator:
    """Coordinate intelligence providers without coupling them to risk scoring."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self.registry = registry if registry is not None else create_default_registry()

    @staticmethod
    def _execution_status(
        provider: IntelligenceProvider,
        data: dict[str, Any],
    ) -> tuple[ProviderStatus, str | None]:
        """Separate provider execution state from intelligence risk signals."""

        if provider.category is not ProviderCategory.IP:
            return ProviderStatus.SUCCESS, None

        status = data.get("status")
        error_code = data.get("error_code")

        if status == "ok":
            return ProviderStatus.SUCCESS, None

        if status in {"invalid", "not_public"}:
            return ProviderStatus.INVALID_INPUT, (
                error_code if isinstance(error_code, str) else None
            )

        if status == "unavailable":
            if error_code == "provider_not_configured":
                return ProviderStatus.NOT_CONFIGURED, error_code

            if error_code == "provider_timeout":
                return ProviderStatus.TIMEOUT, error_code

            return ProviderStatus.UNAVAILABLE, (
                error_code if isinstance(error_code, str) else None
            )

        return ProviderStatus.ERROR, "invalid_provider_response"

    def _execute_category(
        self,
        category: ProviderCategory,
        value: str | None,
        *,
        user_country: str | None = None,
    ) -> tuple[dict[str, Any] | None, list[ProviderExecutionResult]]:
        """Execute the single enabled provider for one supplied input."""

        if not value:
            return None, []

        registered = self.registry.get_providers(
            category,
            enabled_only=False,
        )
        enabled = self.registry.get_providers(category)

        if not enabled:
            executions = [
                ProviderExecutionResult(
                    provider_name=provider.name,
                    category=category,
                    status=ProviderStatus.SKIPPED,
                    error_code="provider_disabled",
                )
                for provider in registered
            ]
            return None, executions

        if len(enabled) > 1:
            executions = [
                ProviderExecutionResult(
                    provider_name=provider.name,
                    category=category,
                    status=ProviderStatus.ERROR,
                    error_code="ambiguous_provider_configuration",
                )
                for provider in enabled
            ]
            return None, executions

        provider = enabled[0]

        try:
            configured = provider.is_configured
        except Exception:
            return None, [
                ProviderExecutionResult(
                    provider_name=provider.name,
                    category=category,
                    status=ProviderStatus.ERROR,
                    error_code="provider_configuration_check_failed",
                )
            ]

        if not configured:
            return None, [
                ProviderExecutionResult(
                    provider_name=provider.name,
                    category=category,
                    status=ProviderStatus.NOT_CONFIGURED,
                    error_code="provider_not_configured",
                )
            ]

        try:
            context: dict[str, Any] = {}

            if category is ProviderCategory.IP:
                context["user_country"] = user_country

            result = provider.analyze(value, **context)

            if not isinstance(result, dict):
                raise TypeError("provider returned a non-dictionary result")

            status, error_code = self._execution_status(provider, result)

            if status is ProviderStatus.ERROR:
                execution = ProviderExecutionResult(
                    provider_name=provider.name,
                    category=category,
                    status=status,
                    error_code=error_code,
                )
                return None, [execution]

            execution = ProviderExecutionResult(
                provider_name=provider.name,
                category=category,
                status=status,
                data=result,
                error_code=error_code,
            )

            return result, [execution]

        except Exception:
            return None, [
                ProviderExecutionResult(
                    provider_name=provider.name,
                    category=category,
                    status=ProviderStatus.ERROR,
                    error_code="provider_execution_failed",
                )
            ]

    def analyze_inputs(
        self,
        *,
        email: str | None = None,
        phone: str | None = None,
        ip: str | None = None,
        user_country: str | None = None,
    ) -> OrchestrationResult:
        """Analyze supplied intelligence inputs and isolate provider failures."""

        data: dict[ProviderCategory, dict[str, Any] | None] = {}
        executions: list[ProviderExecutionResult] = []

        inputs = (
            (ProviderCategory.EMAIL, email),
            (ProviderCategory.PHONE, phone),
            (ProviderCategory.IP, ip),
        )

        for category, value in inputs:
            result, category_executions = self._execute_category(
                category,
                value,
                user_country=user_country,
            )

            data[category] = result
            executions.extend(category_executions)

        return OrchestrationResult(
            data=data,
            executions=tuple(executions),
        )
