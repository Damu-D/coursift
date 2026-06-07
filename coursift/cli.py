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
def install(
    platform: str = typer.Option(
        "claude", "--platform", "-p",
        help="claude | cursor | copilot | gemini | windsurf | cline | codex | "
             "opencode | zed | aider | agents | all",
    ),
    project: str = typer.Option(".", "--project", help="Project root for project-scoped files"),
    user: bool = typer.Option(False, "--user", help="Claude only: install to ~/.claude (global)"),
):
    """Install Coursift instructions for one or all AI platforms."""
    from coursift.platforms import install_platform, list_platforms

    if platform == "claude" and user:
        from coursift.skill import install_skill
        path = install_skill()
        rprint(f"[green]✓[/green] Claude Code skill installed globally: [bold]{path}[/bold]")
        rprint("\n[bold]Next:[/bold] Run [cyan]coursift build[/cyan] to build your graph.")
        return

    try:
        written = install_platform(platform, project)
    except ValueError as e:
        rprint(f"[red]{e}[/red]")
        raise typer.Exit(1)

    labels = list_platforms()
    if platform == "all":
        rprint(f"[green]✓[/green] Installed Coursift for [bold]all platforms[/bold] "
               f"({len(written)} files):")
    else:
        rprint(f"[green]✓[/green] Installed for [bold]{labels.get(platform, platform)}[/bold]:")
    for p in written:
        rprint(f"  [dim]{p}[/dim]")
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
    project: str = typer.Option(None, "--project", "-p", help="Limit to one project"),
    all_projects: bool = typer.Option(False, "--all", help="Search every project"),
):
    """Build a token-budgeted, grounded context pack (anti context-rot, anti-cost)."""
    from coursift.context_pack import build_context_pack
    from coursift.scope import resolve_scope
    scope, label = resolve_scope(project, all_projects)
    rprint(f"[dim]scope: {label}[/dim]")
    pack = build_context_pack(question, max_tokens=max_tokens, scope=scope)
    print(pack)


@app.command()
def verify(
    symbol: str = typer.Argument(..., help="Function/class/file to verify exists"),
    project: str = typer.Option(None, "--project", "-p", help="Limit to one project"),
    all_projects: bool = typer.Option(False, "--all", help="Search every project"),
):
    """Check if a symbol really exists (anti-hallucination grounding)."""
    from coursift.verify import verify_symbol
    from coursift.scope import resolve_scope
    scope, label = resolve_scope(project, all_projects)
    rprint(f"[dim]scope: {label}[/dim]")
    r = verify_symbol(symbol, scope=scope)
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
    all_projects: bool = typer.Option(False, "--all", help="Show lessons from every project"),
):
    """Show failure lessons mined from your Claude sessions (avoid repeating them)."""
    from coursift.lessons import mine_lessons
    from coursift.config import list_projects
    from coursift.scope import resolve_scope
    scope, label = resolve_scope(project, all_projects)
    rprint(f"[dim]scope: {label}[/dim]")
    found = mine_lessons(list_projects())
    if scope is not None:
        found = [l for l in found if l.project.lower() in scope]
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
    project: str = typer.Option(None, "--project", "-p", help="Limit target to one project"),
    all_projects: bool = typer.Option(False, "--all", help="Match symbol in any project"),
):
    """Blast radius: what depends on this symbol BEFORE you change it."""
    from coursift.impact import blast_radius
    from coursift.scope import resolve_scope
    scope, label = resolve_scope(project, all_projects)
    rprint(f"[dim]scope: {label}[/dim]")
    r = blast_radius(symbol, max_depth=depth, scope=scope)
    if r["status"] == "not_found":
        rprint(f"[yellow]'{symbol}' not found in the graph (scope: {label}).[/yellow]")
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


@app.command()
def duplicates(
    threshold: float = typer.Option(0.6, "--threshold", "-t", help="Similarity 0-1"),
    cross_only: bool = typer.Option(False, "--cross-only", help="Only cross-project"),
):
    """Find near-duplicate functions across projects (extraction candidates)."""
    from coursift.duplicates import find_duplicates, summarize
    results = find_duplicates(threshold=threshold, cross_project_only=cross_only)
    if not results:
        rprint("[green]No significant duplicates found.[/green]")
        return
    s = summarize(results)
    rprint(f"\n[bold]{s['total']} duplicate pair(s)[/bold] "
           f"([yellow]{s['cross_project']} cross-project[/yellow]):\n")
    for r in results[:20]:
        tag = "[yellow]⬡ cross-project[/yellow]" if r["cross_project"] else "[dim]same project[/dim]"
        a, b = r["a"], r["b"]
        rprint(f"  {r['similarity']:.0%} {tag}")
        rprint(f"    {a['label']} [dim]({a['project']} · {Path(a['file']).name}:{a['line']})[/dim]")
        rprint(f"    {b['label']} [dim]({b['project']} · {Path(b['file']).name}:{b['line']})[/dim]")


@app.command()
def consolidate(
    keep_trivial: bool = typer.Option(False, "--keep-trivial", help="Don't prune trivia"),
):
    """Consolidate memory: distill lessons → insights, dedupe, prune (the 'sleep cycle')."""
    from coursift.consolidate import consolidate as run_consolidate
    r = run_consolidate(prune_trivial=not keep_trivial)
    if r["status"] != "ok":
        rprint(f"[yellow]{r['status']}[/yellow]")
        return
    rprint(f"[green]✓ Consolidated.[/green] "
           f"{r['insights_created']} insight(s) distilled · "
           f"{r['concepts_merged']} concept(s) merged · "
           f"{r['trivia_pruned']} trivia pruned")
    for ins in r["insights"][:10]:
        rprint(f"  💡 [cyan]{ins['project']}[/cyan] — {ins['insight']} [dim](evidence: {ins['evidence']})[/dim]")


@app.command()
def constitution():
    """Generate a learned agent constitution (rules distilled from failures)."""
    from coursift.constitution import write_constitution
    path = write_constitution()
    rprint(f"[green]✓[/green] Constitution written: [bold]{path}[/bold]\n")
    console.print(path.read_text(), markup=False, highlight=False)


@app.command()
def preflight(
    project: str = typer.Argument(".", help="Project path (default: current dir)"),
):
    """Proactive briefing from your current git changes (blast radius + coupling + lessons)."""
    from coursift.preflight import preflight as run_preflight
    r = run_preflight(project)
    if r["status"] == "clean":
        rprint(f"[green]{r['message']}[/green]")
        return
    if r["status"] != "ok":
        rprint(f"[yellow]{r['status']}[/yellow]")
        return
    rprint(f"\n[bold cyan]Preflight briefing — {r['project']}[/bold cyan]")
    rprint(f"  Changed: {', '.join(Path(c).name for c in r['changed_files'][:8])}")
    if r["blast_radius"]:
        rprint("\n  [yellow]⚠ Blast radius (these depend on what you're changing):[/yellow]")
        for label, proj, fname in r["blast_radius"][:10]:
            rprint(f"    {label} [dim]({proj} · {fname})[/dim]")
    if r["also_edit"]:
        rprint("\n  [magenta]↔ Historically changed together — consider editing too:[/magenta]")
        for fname, sup, conf in r["also_edit"]:
            rprint(f"    {fname} [dim](together {sup}×, conf {conf})[/dim]")
    if r["relevant_lessons"]:
        rprint("\n  [red]💥 Past failures near here:[/red]")
        for kind, signal, ctx in r["relevant_lessons"]:
            rprint(f"    ({kind}) {signal} — [dim]{ctx}[/dim]")
    if r["decisions"]:
        rprint("\n  [green]📌 Established decisions:[/green]")
        for d in r["decisions"]:
            rprint(f"    {d}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Semantic search across all code"),
    top: int = typer.Option(10, "--top", "-k", help="Number of results"),
    project: str = typer.Option(None, "--project", "-p", help="Limit to one project"),
    all_projects: bool = typer.Option(False, "--all", help="Search every project"),
):
    """Semantic code search across all projects (local TF-IDF, no API)."""
    from coursift.embed import TfidfIndex
    from coursift.graph import load_graph
    from coursift.scope import resolve_scope, in_scope
    scope, label = resolve_scope(project, all_projects)
    rprint(f"[dim]scope: {label}[/dim]")
    graph = load_graph()
    if not graph:
        rprint("[yellow]No graph. Run `coursift build` first.[/yellow]")
        return
    idx = TfidfIndex()
    nodemap = {}
    for n in graph.get("nodes", []):
        if n.get("kind") in ("function", "class", "file") and in_scope(n, scope):
            text = " ".join([n.get("label", ""), n.get("docstring", ""),
                             " ".join(n.get("tokens", []))])
            idx.add(n["id"], text)
            nodemap[n["id"]] = n
    idx.build()
    hits = idx.search(query, top_k=top)
    if not hits:
        rprint("[yellow]No matches.[/yellow]")
        return
    rprint(f"\n[bold]Semantic matches for '{query}':[/bold]\n")
    for nid, score in hits:
        n = nodemap[nid]
        rprint(f"  {score:.2f} [{n.get('kind')}] [cyan]{n.get('label')}[/cyan] "
               f"[dim]({n.get('project')} · {Path(n.get('file','')).name}:{n.get('line',0)})[/dim]")


@app.command()
def cost():
    """Token spend attribution across projects (from session telemetry)."""
    from coursift.cost import analyze_cost
    r = analyze_cost()
    if r["status"] != "ok":
        rprint(f"[yellow]{r['status']}[/yellow]")
        return
    rprint(f"\n[bold]Estimated total spend: [green]${r['total_cost']}[/green][/bold]\n")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Project", style="cyan")
    table.add_column("Cost", justify="right")
    table.add_column("In", justify="right")
    table.add_column("Out", justify="right")
    table.add_column("Cache rd", justify="right")
    table.add_column("Msgs", justify="right")
    for proj, d in r["by_project"].items():
        table.add_row(proj, f"${d['cost']}", f"{d['input']:,}", f"{d['output']:,}",
                      f"{d['cache_read']:,}", str(d["messages"]))
    console.print(table)
    rprint("\n  By model: " + " · ".join(f"{m.split('-')[1] if '-' in m else m}=${c}"
                                          for m, c in r["by_model"].items() if c > 0))
    rprint(f"  [dim]{r['note']}[/dim]")


@app.command()
def onboard(project: str = typer.Argument(..., help="Project name to generate a tour for")):
    """Generate an onboarding guide / codebase tour for a project."""
    from coursift.onboard import write_onboarding
    path = write_onboarding(project)
    rprint(f"[green]✓[/green] Onboarding guide: [bold]{path}[/bold]\n")
    console.print(path.read_text(), markup=False, highlight=False)


@app.command()
def health():
    """Health & tech-debt score per project (synthesizes the whole graph)."""
    from coursift.health import health_report
    r = health_report()
    if r["status"] != "ok":
        rprint(f"[yellow]{r['status']}[/yellow]")
        return
    rprint("\n[bold cyan]Project Health[/bold cyan]\n")
    if not r["projects"]:
        rprint("  [yellow]No code-scanned projects. Run `coursift add <path>` then `build`.[/yellow]")
    for p in r["projects"]:
        color = "green" if p["score"] >= 70 else "yellow" if p["score"] >= 55 else "red"
        rprint(f"  [{color}]{p['score']:.0f}/100[/{color}] [bold]{p['project']}[/bold] "
               f"— {p['grade']} [dim]({p['files']} files, {p['functions']} symbols)[/dim]")
        for reason, pts in p["deductions"]:
            rprint(f"      [dim]−{pts}[/dim] {reason}")
    if r.get("session_only"):
        rprint(f"\n  [dim]Session-only (not code-scanned, run `coursift add`): "
               f"{', '.join(r['session_only'])}[/dim]")


@app.command()
def serve():
    """Start the Coursift MCP server (exposes graph tools to any agent)."""
    rprint("[cyan]Starting Coursift MCP server (stdio)...[/cyan]")
    from coursift.serve import main as serve_main
    serve_main()


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
