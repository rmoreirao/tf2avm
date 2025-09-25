from __future__ import annotations

from pathlib import Path
from .base import agent_step
from schemas import MappingResult, RepoManifest, ConversionResult


@agent_step("converter")
def convert_repo(manifest: RepoManifest, mapping: MappingResult, output_dir: str = "./output") -> ConversionResult:
    # Create a fake converted structure
    out_path = Path(output_dir) / "repo1_avm"
    out_path.mkdir(parents=True, exist_ok=True)
    for fake_file in ["main.tf", "network.tf", "variables.tf", "outputs.tf"]:
        (out_path / fake_file).write_text(
            f"// Converted placeholder for {fake_file}\n// Mappings count: {len(mapping.mappings)}\n"
        )
    return ConversionResult(
        converted_repo_path=str(out_path),
        files_converted=["main.tf", "network.tf", "variables.tf", "outputs.tf"],
    )
