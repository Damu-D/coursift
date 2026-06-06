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
        from coursift.lessons import mine_lessons, lessons_to_nodes_edges
        with console.status("Indexing Claude sessions..."):
            entries = index_sessions(projects)
            session_nodes, session_edges = sessions_to_nodes_edges(entries)
        rprint(f"  [dim]sessions[/dim] — {len(entries)} sessions, {len(session_nodes)} nodes")

        with console.status("Mining failure lessons..."):
            lessons = mine_lessons(projects)
            lesson_nodes, lesson_edges = lessons_to_nodes_edges(lessons)
        session_nodes.extend(lesson_nodes)
        session_edges.extend(lesson_edges)
        rprint(f"  [dim]lessons[/dim] — {len(lessons)} failure lesson(s) mined")

    # Temporal coupling from git history
    from coursift.coupling import detect_all as detect_coupling_all, coupling_to_edges
    with console.status("Mining temporal coupling (git)..."):
        coupling_pairs = detect_coupling_all(projects)
        coupling_edges = coupling_to_edges(coupling_pairs)
    session_edges.extend(coupling_edges)
    if coupling_pairs:
        rprint(f"  [dim]coupling[/dim] — {len(coupling_pairs)} co-change pair(s)")

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


@app.command()
def context(
    question: str = typer.Argument(..., help="What you need context for"),
    max_tokens: int = typer.Option(2000, "--max-tokens", "-t", help="Token budget"),
):
    """Build a token-budgeted, grounded context pack (anti context-rot, anti-cost)."""
    from coursift.context_pack import build_context_pack
    pack = build_context_pack(question, max_tokens=max_tokens)
    print(pack)


@app.command()
def verify(symbol: str = typer.Argument(..., help="Function/class/file to verify exists")):
    """Check if a symbol really exists (anti-hallucination grounding)."""
    from coursift.verify import verify_symbol
    r = verify_symbol(symbol)
    if r["status"] == "found":
        rprint(f"[green]✓ '{r['symbol']}' exists[/green] ({len(r['matches'])} match(es)):")
        for m in r["matches"]:
            doc = f" — {m['doc'][:80]}" if m.get("doc") else ""
            rprint(f"  [{m['kind']}] {m['project']} · {m['file']}:{m['line']}{doc}")
    elif r["status"] == "not_found":
        rprint(f"[red]✗ '{r['symbol']}' does NOT exist in any indexed project.[/red]")
        rprint(f"  [yellow]{r['warning']}[/yellow]")
        if r["suggestions"]:
            rprint("\n  Closest real matches:")
            for s in r["suggestions"]:
                rprint(f"    {s['label']} [{s['kind']}] ({s['project']}) ~{s['similarity']}")
    else:
        rprint(f"[yellow]{r.get('message', r['status'])}[/yellow]")


@app.command()
def deps():
    """Audit third-party dependencies & flag slopsquat/supply-chain risk."""
    from coursift.deps import audit_dependencies
    r = audit_dependencies()
    if r["status"] != "ok":
        rprint(f"[yellow]{r.get('message', r['status'])}[/yellow]")
        return
    for project, data in r["projects"].items():
        rprint(f"\n[bold cyan]{project}[/bold cyan]")
        rprint(f"  third-party: {', '.join(data['third_party']) or '(none)'}")
        rprint(f"  stdlib: {data['stdlib_count']} · local imports: {data['local_imports']}")
        if data["unverified"]:
            rprint(f"  [yellow]unverified ({len(data['unverified'])}):[/yellow] {', '.join(data['unverified'][:20])}")
    rprint(f"\n[dim]{r['note']}[/dim]")


@app.command()
def drift(days: int = typer.Option(30, "--days", "-d", help="Look-back window")):
    """Detect documentation drift — code changed but docs didn't (anti stale-spec)."""
    from coursift.drift import detect_all
    from coursift.config import list_projects
    results = detect_all(list_projects(), days=days)
    if not results:
        rprint("[yellow]No projects to check.[/yellow]")
        return
    for r in results:
        if r["status"] == "drift":
            rprint(f"[red]⚠ {r['project']}[/red] — {r['message']}")
            for f in r.get("sample_code", [])[:5]:
                rprint(f"    [dim]{f}[/dim]")
        elif r["status"] == "ok":
            rprint(f"[green]✓ {r['project']}[/green] — {r['message']}")
        else:
            rprint(f"[dim]· {r['project']} — {r['status']}[/dim]")


@app.command()
def audit():
    """Scan memory for prompt-injection / poisoning (anti memory-poisoning)."""
    from coursift.security import audit_graph
    from coursift.graph import load_graph
    graph = load_graph()
    if not graph:
        rprint("[yellow]No graph. Run `coursift build` first.[/yellow]")
        return
    r = audit_graph(graph)
    color = "green" if r["status"] == "clean" else "red"
    rprint(f"[{color}]{r['summary']}[/{color}]")
    for f in r["flagged"]:
        rprint(f"  [red]⚠[/red] {f['node']} ({f['project']}) — trust={f['trust']} · {', '.join(f['findings'][:3])}")


@app.command()
def forget(older_than: str = typer.Argument(..., help="Age e.g. 90d, 4w, 12h")):
    """Prune stale memory older than a given age (selective forgetting)."""
    from coursift.forget import forget_older_than
    r = forget_older_than(older_than)
    if r["status"] == "ok":
        rprint(f"[green]✓[/green] Removed {r['removed']} stale node(s) older than {r['older_than']}. "
               f"{r['remaining']} remain.")
    else:
        rprint(f"[yellow]{r['status']}[/yellow]")


@app.command()
def lessons(
    project: str = typer.Option(None, "--project", "-p", help="Filter to one project name"),
):
    """Show failure lessons mined from your Claude sessions (avoid repeating them)."""
    from coursift.lessons import mine_lessons
    from coursift.config import list_projects
    found = mine_lessons(list_projects())
    if project:
        found = [l for l in found if project.lower() in l.project.lower()]
    if not found:
        rprint("[green]No failure patterns found in your sessions.[/green]")
        return
    rprint(f"\n[bold]{len(found)} failure lesson(s) — don't repeat these:[/bold]\n")
    icon = {"tool_error": "💥", "user_correction": "🙅", "self_correction": "🔄"}
    for l in found[:30]:
        rprint(f"{icon.get(l.kind, '⚠')} [bold cyan]{l.project}[/bold cyan] "
               f"[dim]({l.kind})[/dim] — {l.signal}")
        rprint(f"   [dim]{l.context[:160]}[/dim]")


@app.command()
def impact(
    symbol: str = typer.Argument(..., help="Symbol/file you want to change"),
    depth: int = typer.Option(3, "--depth", "-d", help="Max dependency depth"),
):
    """Blast radius: what depends on this symbol BEFORE you change it."""
    from coursift.impact import blast_radius
    r = blast_radius(symbol, max_depth=depth)
    if r["status"] == "not_found":
        rprint(f"[yellow]'{symbol}' not found in the graph.[/yellow]")
        return
    if r["status"] != "ok":
        rprint(f"[yellow]{r['status']}[/yellow]")
        return
    color = {"LOW": "green", "MEDIUM": "yellow", "HIGH": "red"}[r["risk"]]
    rprint(f"\n[bold]Blast radius for '{symbol}'[/bold] — risk: [{color}]{r['risk']}[/{color}]")
    rprint(f"  {r['total_impacted']} node(s) depend on it across {len(r['by_project'])} project(s)")
    if r["cross_project"]:
        rprint(f"  [red]⚠ CROSS-PROJECT impact:[/red] {r['by_project']}")
    rprint("\n  Most directly affected:")
    for n in r["top_impacted"][:12]:
        rprint(f"    [{n.get('kind')}] {n.get('label')} ({n.get('project')}) depth={n['depth']}")


@app.command()
def coupling(
    min_support: int = typer.Option(3, "--min-support", help="Min commits together"),
):
    """Files that change together (temporal coupling from git history)."""
    from coursift.coupling import detect_all
    from coursift.config import list_projects
    pairs = detect_all(list_projects())
    pairs = [p for p in pairs if p["support"] >= min_support]
    if not pairs:
        rprint("[yellow]No strong co-change coupling found.[/yellow]")
        return
    rprint(f"\n[bold]{len(pairs)} co-change pair(s) — edit one, check the other:[/bold]\n")
    for p in pairs[:25]:
        from pathlib import Path as _P
        a, b = _P(p["file_a"]).name, _P(p["file_b"]).name
        rprint(f"  [cyan]{p['project']}[/cyan] · {a} ↔ {b} "
               f"[dim](together {p['support']}x, confidence {p['confidence']})[/dim]")


@app.command(name="secrets")
def secrets_scan():
    """Scan indexed memory for leaked credentials (anti data-exfiltration)."""
    from coursift.security import detect_secrets
    from coursift.graph import load_graph
    graph = load_graph()
    if not graph:
        rprint("[yellow]No graph. Run `coursift build` first.[/yellow]")
        return
    flagged = []
    for n in graph.get("nodes", []):
        blob = " ".join([
            n.get("label", ""), n.get("context", ""),
            " ".join(n.get("decisions", []) or []),
        ])
        s = detect_secrets(blob)
        if s:
            flagged.append((n.get("project", "?"), n.get("kind"), s))
    if not flagged:
        rprint("[green]✓ No leaked secrets in indexed memory.[/green]")
        return
    rprint(f"[red]⚠ {len(flagged)} memory node(s) contain credential patterns:[/red]")
    for proj, kind, labels in flagged[:20]:
        rprint(f"  [{kind}] {proj} — {', '.join(labels)}")
    rprint("\n[yellow]Coursift redacts these on write, but rotate any real ones.[/yellow]")


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
