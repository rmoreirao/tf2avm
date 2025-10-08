from pathlib import Path

from agents.repo_scanner import scan_repo
from schemas import RepoInput


def test_repo_scanner_parses_local_fixture():
    fixture_repo = Path(__file__).parent / "fixtures" / "repo_basic"
    manifest = scan_repo(RepoInput(repo_folder=str(fixture_repo)))

    # Files discovered
    paths = {f.path for f in manifest.files}
    assert paths == {"main.tf", "network.tf", "variables.tf", "outputs.tf"}

    # Resources
    resources = {(r['type'], r['name']) for f in manifest.files for r in f.resources}
    assert ("azurerm_virtual_network", "vnet1") in resources
    assert ("azurerm_subnet", "subnet1") in resources

    # Variables
    var_names = {v['name'] for v in manifest.variables}
    assert "location" in var_names
    loc_var = next(v for v in manifest.variables if v['name'] == 'location')
    assert loc_var['default'] == 'westeurope'

    # Outputs
    out_names = {o['name'] for o in manifest.outputs}
    assert "vnet_id" in out_names

    # Providers (from resources inference)
    # Provider blocks not defined, so providers list may be empty until provider blocks exist.
    # Accept empty list; future enhancement may infer from resource types.
    assert manifest.providers == [] or 'azurerm' in manifest.providers
