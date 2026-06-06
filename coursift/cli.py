"""
Coursift CLI — the main entry point.

Commands:
  coursift add <path>      Register a project
  coursift remove <path>   Unregister a project
  coursift list            List registered projects
  coursift build           Build the unified graph
  coursift query "<q>"     Ask a question about the graph
  coursift sessions        Show indexed Claude sessions
  coursift install         Install the Claude Code skill
  coursift uninstall       Remove the Claude Code skill
  coursift status          Show graph stats
  coursift open            Open the HTML visualization
"""

import subprocess
import sys
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.progress import track

app = typer.Typer(
    name="coursift",
    help="Cross-project knowledge graph and memory layer for Claude Code.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


@app.command()
def add(path: str = typer.Argument(..., help="Path to the project to register")):
    """Register a project to include in the knowledge graph."""
    from coursift.config import add_project
    ok, msg = add_project(path)
    if ok:
        rprint(f"[green]✓[/green] Registered: [bold]{msg}[/bold]")
    else:
        rprint(f"[yellow]![/yellow] {msg}")


@app.command()
def remove(path: str = typer.Argument(..., help="Path of the project to remove")):
    """Unregister a project from the knowledge graph."""
    from coursift.config import remove_project
    ok, msg = remove_project(path)
    if ok:
        rprint(f"[green]✓[/green] Removed: [bold]{msg}[/bold]")
    else:
        rprint(f"[red]✗[/red] {msg}")


@app.command(name="list")
def list_cmd():
    """List all registered projects."""
    from coursift.config import list_projects
    projects = list_projects()
    if not projects:
        rprint("[yellow]No projects registered. Run:[/yellow] coursift add <path>")
        return
    table = Table(title="Registered Projects", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Path", style="cyan")
    table.add_column("Exists", width=8)
    for i, p in enumerate(projects, 1):
        exists = "[green]✓[/green]" if Path(p).exists() else "[red]✗[/red]"
        table.add_row(str(i), p, exists)
    console.print(table)


@app.command()
def build(
    no_sessions: bool = typer.Option(False, "--no-sessions", help="Skip Claude session indexing"),
    no_viz: bool = typer.Option(False, "--no-viz", help="Skip HTML visualization"),
):
    """Build the unified knowledge graph across all registered projects."""
    from coursift.config import list_projects, GRAPH_FILE, CONFIG_DIR
    from coursift.scanner import scan_project
    from coursift.sessions import index_sessions, sessions_to_nodes_edges
    from coursift.graph import build_graph, save_graph, graph_summary
    from coursift.viz import generate_html
    from coursift.report import generate_report

    projects = list_projects()
    if not projects:
        rprint("[red]No projects registered.[/red] Run: [bold]coursift add <path>[/bold]")
        raise typer.Exit(1)

    all_nodes, all_edges = [], []

    rprint(f"\n[bold cyan]Coursift[/bold cyan] — scanning {len(projects)} project(s)...\n")

    for project_path in track(projects, description="Scanning code..."):
        if not Path(project_path).exists():
            rprint(f"  [yellow]⚠ Skipping missing path:[/yellow] {project_path}")
            continue
        nodes, edges = scan_project(project_path)
        all_nodes.extend(nodes)
        all_edges.extend(edges)
        rprint(f"  [dim]{Path(project_path).name}[/dim] — {len(nodes)} nodes, {len(edges)} edges")

    session_nodes, session_edges = [], []
    if not no_sessions:
        with console.status("Indexing Claude sessions..."):
            entries = index_sessions(projects)
            session_nodes, session_edges = sessions_to_nodes_edges(entries)
        rprint(f"  [dim]sessions[/dim] — {len(entries)} sessions, {len(session_nodes)} nodes")

    with console.status("Building graph..."):
        graph = build_graph(all_nodes, all_edges, session_nodes, session_edges)
        graph_file = save_graph(graph)

    rprint(f"\n[green]✓[/green] Graph saved: [bold]{graph_file}[/bold]")
    rprint(f"  {graph_summary(graph)}")

    if not no_viz:
        html_path = CONFIG_DIR / "graph.html"
        generate_html(graph, html_path)
        rprint(f"[green]✓[/green] Visualization: [bold]{html_path}[/bold]")

    report_path = CONFIG_DIR / "GRAPH_REPORT.md"
    generate_report(graph, report_path)
    rprint(f"[green]✓[/green] Report: [bold]{report_path}[/bold]")

    rprint("\n[bold]Next:[/bold] [cyan]coursift query \"<your question>\"[/cyan]")


@app.command()
def query(question: str = typer.Argument(..., help="Natural language question about your projects")):
    """Ask a natural language question about the unified knowledge graph."""
    from coursift.query import query_graph
    with console.status(f"Querying graph: [italic]{question}[/italic]"):
        answer = query_graph(question)
    rprint(f"\n[bold cyan]Answer:[/bold cyan]\n\n{answer}\n")


@app.command()
def sessions():
    """Show indexed Claude Code sessions and their extracted decisions."""
    from coursift.config import list_projects
    from coursift.sessions import index_sessions

    projects = list_projects()
    entries = index_sessions(projects)

    if not entries:
        rprint("[yellow]No Claude sessions found.[/yellow]")
        rprint(f"Expected location: [dim]~/.claude/projects/[/dim]")
        return

    rprint(f"\n[bold]Found {len(entries)} session(s)[/bold]\n")
    for entry in entries[:20]:
        rprint(f"[bold cyan]{entry.project_name}[/bold cyan] — session [dim]{entry.session_id[:8]}[/dim]")
        if entry.decisions:
            for dec in entry.decisions[:2]:
                rprint(f"  [dim]decision:[/dim] {dec}")
        if entry.concepts:
            rprint(f"  [dim]concepts:[/dim] {', '.join(entry.concepts[:6])}")
        rprint()


@app.command()
def install():
    """Install the Coursift skill into Claude Code (runs in every session)."""
    from coursift.skill import install_skill
    path = install_skill()
    rprint(f"[green]✓[/green] Skill installed: [bold]{path}[/bold]")
    rprint("  Claude Code will now use the knowledge graph in every session.")
    rprint("\n[bold]Next:[/bold] Run [cyan]coursift build[/cyan] to build your graph.")


@app.command()
def uninstall():
    """Remove the Coursift skill from Claude Code."""
    from coursift.skill import uninstall_skill
    if uninstall_skill():
        rprint("[green]✓[/green] Skill removed from Claude Code.")
    else:
        rprint("[yellow]Skill was not installed.[/yellow]")


@app.command()
def status():
    """Show current graph stats."""
    from coursift.graph import load_graph, graph_summary
    from coursift.config import list_projects, GRAPH_FILE

    projects = list_projects()
    rprint(f"\n[bold cyan]Coursift Status[/bold cyan]")
    rprint(f"  Registered projects: [bold]{len(projects)}[/bold]")
    for p in projects:
        exists = "[green]✓[/green]" if Path(p).exists() else "[red]missing[/red]"
        rprint(f"    {exists} {p}")

    graph = load_graph()
    if graph:
        rprint(f"\n  Graph: {graph_summary(graph)}")
        rprint(f"  Location: [dim]{GRAPH_FILE}[/dim]")
    else:
        rprint("\n  [yellow]No graph built yet.[/yellow] Run: [cyan]coursift build[/cyan]")


@app.command(name="open")
def open_viz():
    """Open the HTML visualization in your default browser."""
    from coursift.config import CONFIG_DIR
    html = CONFIG_DIR / "graph.html"
    if not html.exists():
        rprint("[red]No visualization found.[/red] Run: [cyan]coursift build[/cyan]")
        raise typer.Exit(1)
    subprocess.run(["open", str(html)], check=False)
    rprint(f"[green]✓[/green] Opened: [bold]{html}[/bold]")


@app.callback(invoke_without_command=True)
def version_check(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
):
    if version:
        from coursift import __version__
        rprint(f"coursift {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
