from __future__ import annotations

import shutil
from pathlib import Path

from orchestrator.graph import run_workflow


def test_e2e_fixture_repo_basic(tmp_path):
    """End-to-end test using a committed dummy Terraform repo fixture.

    Validates: workflow runs, report generated, converted files created,
    and deterministic failure status (current stub validator).
    """

    # Arrange
    fixture_repo = Path(__file__).parent / "fixtures" / "repo_basic"
    assert fixture_repo.exists(), "Fixture repo missing"

    # Clean previous output to ensure deterministic assertions
    out_root = Path("./output")
    if out_root.exists():
        shutil.rmtree(out_root)

    # Act
    outcome = run_workflow(str(fixture_repo))

    # Assert outcome basics
    assert outcome.status == "failed"  # stub validator forces failure
    assert outcome.report_path is not None, "Report path missing"
    report_file = Path(outcome.report_path)
    assert report_file.exists(), "Report file not created"

    # Report content checks (substring asserts for forward compatibility)
    report_text = report_file.read_text(encoding="utf-8")
    assert "# Conversion Report: repo1" in report_text
    assert "## ✅ Converted Files" in report_text
    assert "## ⚠️ Issues Found" in report_text
    assert "azurerm_virtual_network" in report_text
    assert "avm-res-network-virtualnetwork" in report_text
    assert "azurerm_subnet" in report_text
    assert "avm-res-network-subnet" in report_text
    assert "Missing required variable 'dns_servers'" in report_text

    # Converted repo artifacts (from converter stub)
    conv_dir = Path("./output/repo1_avm")
    assert conv_dir.exists(), "Converted repo directory missing"
    for fname in ["main.tf", "network.tf", "variables.tf", "outputs.tf"]:
        fpath = conv_dir / fname
        assert fpath.exists(), f"Converted file missing: {fname}"
        content = fpath.read_text(encoding="utf-8")
        assert content.startswith("// Converted placeholder"), f"Unexpected content in {fname}"

    # Idempotency: run again and ensure status stable
    outcome2 = run_workflow(str(fixture_repo))
    assert outcome2.status == outcome.status
