"""Stub AVM index retrieval."""

def fetch_avm_index(resource_types):  # pragma: no cover - stub
    return {rt: {"module": f"avm-module-for-{rt}", "version": "0.0.0"} for rt in resource_types}
