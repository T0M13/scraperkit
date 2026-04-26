"""
ScraperKit CLI — entry point for all commands.

Usage:
    scraperkit run project.yaml
    scraperkit serve
    scraperkit runs [--project NAME] [--limit N]
    scraperkit show <run_id>
"""
from __future__ import annotations

import sys
from pathlib import Path

import typer

app = typer.Typer(
    name="scraperkit",
    help="Config-driven scraping and automation platform.",
    add_completion=False,
)


@app.command()
def run(
    config_path: Path = typer.Argument(..., help="Path to YAML/JSON project config"),
    output_dir: str | None = typer.Option(None, "--output", "-o", help="Override output directory"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Logging level"),
    db: str = typer.Option("scraperkit.db", "--db", help="SQLite database path"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate config and print steps without running"),
    run_id: str | None = typer.Option(None, "--run-id", hidden=True, help="Override run ID (used by API job manager)"),
):
    """Run a scraping workflow defined in a YAML/JSON config file."""
    from scraperkit.core.config import load_config
    from scraperkit.core.runner import WorkflowRunner
    from scraperkit.logging.db import RunStore
    from scraperkit.logging.setup import configure_logging

    try:
        config = load_config(config_path)
    except Exception as exc:
        typer.echo(f"Error loading config: {exc}", err=True)
        raise typer.Exit(1)

    if dry_run:
        typer.echo(f"Project: {config.name}")
        typer.echo(f"URLs:    {config.start_urls}")
        typer.echo(f"Steps:   {' → '.join(config.workflow)}")
        typer.echo("(dry-run — not executing)")
        return

    out = output_dir or config.output.directory
    log_dir = Path(out) / config.name / "logs"
    configure_logging(level=log_level, log_dir=log_dir, project_name=config.name)

    store = RunStore(db)
    runner = WorkflowRunner(config, output_dir=out, run_id=run_id)

    import importlib
    importlib.import_module("scraperkit.steps")
    importlib.import_module("scraperkit.extractors")

    try:
        ctx = runner.run()
        store.start_run(ctx.run_id, config.name, ctx.started_at)
        for result in ctx.step_results:
            store.save_step(
                run_id=ctx.run_id,
                step=result.step,
                status=result.status,
                duration_s=result.duration_s,
                items_in=result.items_in,
                items_out=result.items_out,
                output_files=result.output_files,
                error=result.error,
                meta=result.meta,
            )
        failed_steps = [r for r in ctx.step_results if r.status == "error"]
        final_status = "failed" if failed_steps else "success"
        store.finish_run(ctx.run_id, final_status, len(ctx.items))

        if failed_steps:
            typer.echo(f"Workflow finished with errors in: {[r.step for r in failed_steps]}", err=True)
            raise typer.Exit(1)
        else:
            typer.echo(f"Workflow '{config.name}' completed. {len(ctx.items)} items.")
    except KeyboardInterrupt:
        typer.echo("Interrupted.", err=True)
        raise typer.Exit(130)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
    db: str = typer.Option("scraperkit.db", "--db", help="SQLite database path"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes"),
):
    """Start the ScraperKit web dashboard and API server."""
    try:
        import uvicorn
    except ImportError:
        typer.echo("uvicorn is required. Run: pip install uvicorn", err=True)
        raise typer.Exit(1)

    import os
    os.environ["SCRAPERKIT_DB"] = db
    typer.echo(f"Starting ScraperKit dashboard at http://{host}:{port}")
    uvicorn.run(
        "scraperkit.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command(name="runs")
def list_runs(
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project name"),
    limit: int = typer.Option(20, "--limit", "-n"),
    db: str = typer.Option("scraperkit.db", "--db"),
):
    """List recent workflow runs."""
    from scraperkit.logging.db import RunStore
    store = RunStore(db)
    runs = store.list_runs(project=project, limit=limit)
    if not runs:
        typer.echo("No runs found.")
        return
    typer.echo(f"{'RUN ID':<12} {'PROJECT':<20} {'STATUS':<10} {'STARTED':<22} {'ITEMS':<8} {'DURATION'}")
    typer.echo("-" * 90)
    for r in runs:
        dur = f"{r['duration_s']:.1f}s" if r.get("duration_s") is not None else "—"
        typer.echo(
            f"{r['run_id']:<12} {r['project']:<20} {r['status']:<10} "
            f"{r['started_at'][:19]:<22} {r.get('item_count', '—')!s:<8} {dur}"
        )


@app.command()
def show(
    run_id: str = typer.Argument(..., help="Run ID to inspect"),
    db: str = typer.Option("scraperkit.db", "--db"),
):
    """Show detailed step-by-step results for a run."""
    from scraperkit.logging.db import RunStore
    store = RunStore(db)
    run = store.get_run(run_id)
    if not run:
        typer.echo(f"Run '{run_id}' not found.", err=True)
        raise typer.Exit(1)

    typer.echo(f"\nRun: {run['run_id']}  Project: {run['project']}  Status: {run['status']}")
    typer.echo(f"Started: {run['started_at']}  Duration: {run.get('duration_s', '—')}s  Items: {run.get('item_count', '—')}")
    typer.echo("\nSteps:")
    for step in run.get("steps", []):
        icon = "✓" if step["status"] == "success" else "✗"
        typer.echo(
            f"  {icon} {step['step']:<22} {step['status']:<10} "
            f"{step.get('duration_s', 0):.2f}s  "
            f"in:{step.get('items_in', 0)} → out:{step.get('items_out', 0)}"
        )
        if step.get("error"):
            typer.echo(f"      ERROR: {step['error']}")


def main():
    # Ensure built-in steps and extractors are registered before any command
    import importlib
    importlib.import_module("scraperkit.steps")
    importlib.import_module("scraperkit.extractors")
    app()


if __name__ == "__main__":
    main()
