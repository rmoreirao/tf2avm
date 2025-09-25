from __future__ import annotations

from .base import agent_step
from schemas import ConversionResult, ValidationResult, ValidationErrorItem


@agent_step("validator")
def validate(conversion: ConversionResult) -> ValidationResult:
    # Stub always returns failed for demonstration
    return ValidationResult(
        status="failed",
        errors=[
            ValidationErrorItem(
                tool="terraform", message="Missing required variable 'dns_servers'."
            )
        ],
        warnings=[],
    )
