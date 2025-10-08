from __future__ import annotations

from .base import agent_step
from schemas import RepoManifest, AVMIndex, MappingResult, MappingEntry


@agent_step("mapping")
def map_resources(manifest: RepoManifest, avm_index: AVMIndex) -> MappingResult:
    index_lookup = {e.resource_type: e for e in avm_index.entries}
    mappings = []
    unmapped = []
    for f in manifest.files:
        for r in f.resources:
            key = r["type"]
            if key in index_lookup:
                mapped_to = index_lookup[key].avm_module
                confidence = 0.95 if "virtual_network" in mapped_to else 0.90
                mappings.append(
                    MappingEntry(
                        original=f"{r['type']}.{r['name']}",
                        mapped_to=mapped_to,
                        confidence=confidence,
                    )
                )
            else:
                unmapped.append(f"{r['type']}.{r['name']}")
    return MappingResult(mappings=mappings, unmapped=unmapped)
