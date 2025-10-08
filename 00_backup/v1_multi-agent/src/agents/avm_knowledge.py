from __future__ import annotations

from .base import agent_step
from schemas import RepoManifest, AVMIndex, AVMIndexEntry


@agent_step("avm_knowledge")
def fetch_index(manifest: RepoManifest) -> AVMIndex:
    # Stub: derive resource types from manifest
    resource_types = []
    for f in manifest.files:
        for r in f.resources:
            if r["type"] not in resource_types:
                resource_types.append(r["type"])
    entries = []
    for rt in resource_types:
        if rt == "azurerm_virtual_network":
            entries.append(
                AVMIndexEntry(
                    resource_type=rt,
                    avm_module="avm-res-network-virtualnetwork",
                    version="1.2.3",
                )
            )
        elif rt == "azurerm_subnet":
            entries.append(
                AVMIndexEntry(
                    resource_type=rt,
                    avm_module="avm-res-network-subnet",
                    version="2.0.1",
                )
            )
    return AVMIndex(entries=entries)
