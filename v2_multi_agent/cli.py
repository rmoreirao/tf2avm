#!/usr/bin/env python3
"""
Command-line interface for the Terraform to AVM converter v2.
"""

import asyncio
import typer
from pathlib import Path
from typing import Optional

from main import TerraformAVMOrchestrator
from config.logging import setup_logging


app = typer.Typer(
    name="tf2avm-v2",
    help="Convert Terraform configurations to use Azure Verified Modules (AVM)",
    add_completion=False
)


@app.command()
def convert(
    repo_path: str = typer.Argument(..., help="Path to the Terraform repository to convert"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="Output directory for converted files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Convert a Terraform repository to use Azure Verified Modules."""
    
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    logger = setup_logging(log_level)
    
    # Validate input path
    repo_path_obj = Path(repo_path)
    if not repo_path_obj.exists():
        typer.echo(f"Error: Repository path '{repo_path}' does not exist.", err=True)
        raise typer.Exit(1)
    
    if not repo_path_obj.is_dir():
        typer.echo(f"Error: Repository path '{repo_path}' is not a directory.", err=True)
        raise typer.Exit(1)
    
    # Check for .tf files
    tf_files = list(repo_path_obj.glob("**/*.tf"))
    if not tf_files:
        typer.echo(f"Error: No Terraform files (.tf) found in '{repo_path}'.", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"Found {len(tf_files)} Terraform files in {repo_path}")
    
    async def run_conversion():
        orchestrator = TerraformAVMOrchestrator()
        try:
            typer.echo("Initializing agents...")
            await orchestrator.initialize()
            
            typer.echo("Starting conversion process...")
            typer.echo("Note: This is a fully autonomous process. No human intervention required.")
            result = await orchestrator.convert_repository(repo_path, output_dir)
            
            if result["status"] == "completed":
                typer.echo("✅ Conversion completed successfully!")
                typer.echo(f"📁 Output directory: {result['output_directory']}")
                typer.echo(f"⏰ Completed at: {result['timestamp']}")
            else:
                typer.echo(f"❌ Conversion failed: {result.get('error', 'Unknown error')}", err=True)
                raise typer.Exit(1)
                
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            typer.echo(f"❌ Conversion failed: {e}", err=True)
            raise typer.Exit(1)
        finally:
            await orchestrator.cleanup()
    
    # Run the async conversion
    asyncio.run(run_conversion())


@app.command()
def test():
    """Run a test conversion using the fixture repository."""
    
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "repo_tf_basic"
    
    if not fixture_path.exists():
        typer.echo("Error: Test fixture repository not found.", err=True)
        typer.echo(f"Expected location: {fixture_path}")
        raise typer.Exit(1)
    
    typer.echo("Running test conversion with fixture repository...")
    
    # Use the convert command with the fixture path
    convert(str(fixture_path), verbose=True)


@app.command()
def validate():
    """Validate the environment and configuration."""
    
    typer.echo("🔍 Validating environment...")
    
    try:
        from config.settings import validate_environment
        validate_environment()
        typer.echo("✅ Environment validation passed")
    except Exception as e:
        typer.echo(f"❌ Environment validation failed: {e}", err=True)
        typer.echo("\nPlease check:")
        typer.echo("1. .env file exists with required Azure OpenAI configuration")
        typer.echo("2. Azure OpenAI service is accessible")
        typer.echo("3. Docker is running (for Terraform MCP server)")
        raise typer.Exit(1)
    
    # Test Docker availability
    import subprocess
    try:
        result = subprocess.run(["docker", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            typer.echo("✅ Docker is available")
        else:
            typer.echo("⚠️  Docker may not be available - this could affect Terraform MCP functionality")
    except FileNotFoundError:
        typer.echo("⚠️  Docker not found - this could affect Terraform MCP functionality")
    
    typer.echo("🎉 Configuration validation completed")


@app.command()
def version():
    """Show version information."""
    typer.echo("Terraform to AVM Converter v2.0.0")
    typer.echo("Multi-agent system using Semantic Kernel Handoff Orchestration")


if __name__ == "__main__":
    app()