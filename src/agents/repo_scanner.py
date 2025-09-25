from __future__ import annotations

from .base import agent_step
from schemas import RepoInput, RepoManifest, FileManifest


@agent_step("repo_scanner")
def scan_repo(repo_input: RepoInput) -> RepoManifest:
    # Stubbed data per spec
    files = [
        FileManifest(path="main.tf", resources=[{"type": "azurerm_virtual_network", "name": "vnet1"}]),
        FileManifest(path="network.tf", resources=[{"type": "azurerm_subnet", "name": "subnet1"}]),
    ]
    manifest = RepoManifest(
        files=files,
        variables=[{"name": "location", "default": "westeurope"}],
        outputs=[{"name": "vnet_id"}],
        providers=["azurerm"],
        terraform_version="1.6.2",
    )
    return manifest
