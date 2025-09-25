from agents.repo_scanner import scan_repo
from agents.avm_knowledge import fetch_index
from agents.mapping import map_resources
from agents.converter import convert_repo
from agents.validator import validate
from agents.reviewer import build_report
from schemas import RepoInput


def test_agent_chain_stubs(tmp_path):
    repo_input = RepoInput(repo_url="https://example/repo.git")
    manifest = scan_repo(repo_input)
    index = fetch_index(manifest)
    mapping = map_resources(manifest, index)
    conversion = convert_repo(manifest, mapping, output_dir=str(tmp_path))
    validation = validate(conversion)
    report = build_report(mapping, validation, conversion)

    assert manifest.files
    assert index.entries
    assert mapping.mappings
    assert conversion.converted_repo_path
    assert validation.errors
    assert "Conversion Report" in report.markdown
