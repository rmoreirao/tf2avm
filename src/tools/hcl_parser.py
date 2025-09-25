"""Stub HCL parser - returns placeholder structures.

Will be replaced with real parsing using python-hcl2 later.
"""

def parse_directory(path: str):  # pragma: no cover - stub
    return {
        "files": ["main.tf", "network.tf"],
        "resources": ["azurerm_virtual_network", "azurerm_subnet"],
    }
