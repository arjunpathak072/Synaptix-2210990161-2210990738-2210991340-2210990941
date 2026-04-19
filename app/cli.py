"""CLI interface for Synaptix."""

import logging
from pathlib import Path

import click

from app.graph import build_graph


@click.command()
@click.option(
    "--path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Path to the Python repository to analyze",
)
@click.option(
    "--chat",
    is_flag=True,
    default=False,
    help="Launch interactive TUI to ask questions about the codebase",
)
@click.option(
    "--web",
    is_flag=True,
    default=False,
    help="Launch Synaptix Explorer web UI (diagram + chat)",
)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Verbose logging")
def main(path: str, chat: bool, web: bool, verbose: bool) -> None:
    """Synaptix - Build a Mental Map of any Python repository."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    repo_path = str(Path(path).resolve())

    db_path = Path(repo_path) / ".synaptix_db"
    has_index = False
    if db_path.exists():
        import chromadb

        try:
            c = chromadb.PersistentClient(path=str(db_path))
            c.get_collection("codebase")
            has_index = True
        except Exception:
            pass

    has_output = (Path(repo_path) / "synaptix_output.md").exists()
    run_pipeline = not (chat or web) or not has_index or not has_output

    if run_pipeline:
        click.echo(f"Scanning: {repo_path}\n")
        graph = build_graph()
        result = graph.invoke({"repo_path": repo_path})

        if result.get("mermaid_output"):
            click.echo("\nDependency Graph (Mermaid):\n")
            click.echo(result["mermaid_output"])
        if result.get("output_file"):
            click.echo(f"\nSaved to: {result['output_file']}")

    if web:
        from app.web import run_web

        run_web(repo_path)
    elif chat:
        from app.tui import run_tui

        run_tui(repo_path)
