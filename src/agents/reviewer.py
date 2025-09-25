from __future__ import annotations

from datetime import datetime
from .base import agent_step
from schemas import MappingResult, ValidationResult, ConversionResult, ReviewReport

REPORT_TEMPLATE = """# Conversion Report: repo1

## ✅ Converted Files
- main.tf → AVM
- network.tf → AVM
- variables.tf → AVM
- outputs.tf → AVM

## ✅ Successful Mappings
{mappings}

## ⚠️ Issues Found
{issues}

## 🔧 Next Steps
- Add required missing variables before deployment.

## 📂 Converted Repo Location
`{path}`

_Generated {ts}_
"""


@agent_step("reviewer")
def build_report(mapping: MappingResult, validation: ValidationResult, conversion: ConversionResult) -> ReviewReport:
    mappings_list = [f"- {m.original} → {m.mapped_to}" for m in mapping.mappings]
    issues_list = [f"- {e.tool}: {e.message}" for e in validation.errors] or ["- None"]
    markdown = REPORT_TEMPLATE.format(
        mappings="\n".join(mappings_list),
        issues="\n".join(issues_list),
        path=conversion.converted_repo_path,
        ts=datetime.utcnow().isoformat(),
    )
    return ReviewReport(markdown=markdown)
