from __future__ import annotations

from langgraph.graph import StateGraph, END
from typing import Dict, Any

from schemas import RepoInput, FinalOutcome
from orchestrator.state import OrchestratorState
from agents.repo_scanner import scan_repo
from agents.avm_knowledge import fetch_index
from agents.mapping import map_resources
from agents.converter import convert_repo
from agents.validator import validate
from agents.reviewer import build_report
from config.settings import get_settings
from config.logging import setup_logging

_logger = setup_logging()


def _node_repo_scanner(state: Dict[str, Any]):
    repo_input: RepoInput = state["repo_input"]
    state["repo_manifest"] = scan_repo(repo_input)
    return state


def _node_avm_knowledge(state: Dict[str, Any]):
    state["avm_index"] = fetch_index(state["repo_manifest"])
    return state


def _node_mapping(state: Dict[str, Any]):
    state["mapping_result"] = map_resources(state["repo_manifest"], state["avm_index"])
    return state


def _node_conversion(state: Dict[str, Any]):
    settings = get_settings()
    state["conversion_result"] = convert_repo(
        state["repo_manifest"], state["mapping_result"], output_dir=settings.output_dir
    )
    return state


def _node_validation(state: Dict[str, Any]):
    state["validation_result"] = validate(state["conversion_result"])
    return state


def _node_reviewer(state: Dict[str, Any]):
    state["review_report"] = build_report(
        state["mapping_result"], state["validation_result"], state["conversion_result"]
    )
    return state


def _node_finalize(state: Dict[str, Any]):
    vr = state["validation_result"]
    cr = state["conversion_result"]
    rr = state["review_report"]
    if vr.status == "success":
        fo = FinalOutcome(
            status="success", converted_repo_path=cr.converted_repo_path, report_path=None
        )
    else:
        # Persist report to file
        from pathlib import Path
        settings = get_settings()
        report_dir = Path(settings.output_dir) / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "report_repo1.md"
        report_path.write_text(rr.markdown)
        fo = FinalOutcome(
            status="failed", converted_repo_path=None, report_path=str(report_path)
        )
    state["final_outcome"] = fo
    return state


def build_graph():
    g = StateGraph(OrchestratorState)
    g.add_node("repo_scanner", _node_repo_scanner)
    g.add_node("avm_knowledge", _node_avm_knowledge)
    g.add_node("mapping", _node_mapping)
    g.add_node("conversion", _node_conversion)
    g.add_node("validation", _node_validation)
    g.add_node("review", _node_reviewer)
    g.add_node("finalize", _node_finalize)

    g.set_entry_point("repo_scanner")
    g.add_edge("repo_scanner", "avm_knowledge")
    g.add_edge("avm_knowledge", "mapping")
    g.add_edge("mapping", "conversion")
    g.add_edge("conversion", "validation")
    g.add_edge("validation", "review")
    g.add_edge("review", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


def run_workflow(repo_url: str) -> FinalOutcome:
    graph = build_graph()
    initial_state = {"repo_input": RepoInput(repo_url=repo_url)}
    final_state = graph.invoke(initial_state)
    outcome: FinalOutcome = final_state["final_outcome"]
    _logger.info("workflow.complete", status=outcome.status, report=outcome.report_path)
    return outcome
