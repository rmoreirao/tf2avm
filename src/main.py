from __future__ import annotations

import json
import typer
from orchestrator.graph import run_workflow

app = typer.Typer(add_completion=False)


@app.command()
def migrate(repo_url: str = typer.Option(..., help="Repo URL or path")):
    """Run the Terraform -> AVM migration workflow (stub outputs)."""
    outcome = run_workflow(repo_url)
    typer.echo(json.dumps(outcome.model_dump(), indent=2))


if __name__ == "__main__":  # pragma: no cover
    app()
