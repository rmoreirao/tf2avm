"""Stub Terraform CLI wrappers."""

def terraform_validate(path: str):  # pragma: no cover - stub
    return {
        "status": "failed",
        "errors": [
            {"tool": "terraform", "message": "Missing required variable 'dns_servers'."}
        ],
        "warnings": [],
    }
