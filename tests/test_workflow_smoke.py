from orchestrator.graph import run_workflow


def test_run_workflow_smoke():
    outcome = run_workflow("https://example.com/repo.git")
    assert outcome.status in {"success", "failed"}
    assert outcome.report_path or outcome.converted_repo_path
