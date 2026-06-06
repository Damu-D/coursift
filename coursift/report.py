"""
Markdown report generator — GRAPH_REPORT.md with highlights, decisions, and suggested questions.
"""

from pathlib import Path
from datetime import datetime


def generate_report(graph: dict, output_path) -> None:
    stats = graph.get("stats", {})
    nodes = graph.get("nodes", [])
    projects = stats.get("projects", [])

    god_nodes = [n for n in nodes if n.get("god_node")][:10]
    cross_project = [n for n in nodes if n.get("cross_project")][:10]
    sessions = [n for n in nodes if n.get("kind") == "session"]

    all_decisions = []
    for s in sessions:
        for dec in s.get("decisions", [])[:3]:
            all_decisions.append((s.get("project", ""), dec))

    lines = [
        "# Coursift Graph Report",
        f"\n> Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
        f"{stats.get('total_nodes', 0)} nodes · {stats.get('total_edges', 0)} edges · "
        f"{len(projects)} project(s)",
        "",
        "---",
        "",
        "## Projects",
        "",
    ]
    for p in projects:
        proj_nodes = [n for n in nodes if n.get("project") == p]
        functions = sum(1 for n in proj_nodes if n.get("kind") == "function")
        classes = sum(1 for n in proj_nodes if n.get("kind") == "class")
        files = sum(1 for n in proj_nodes if n.get("kind") == "file")
        lines.append(f"- **{p}** — {files} files · {functions} functions · {classes} classes")

    lines += [
        "",
        "---",
        "",
        "## God Nodes",
        "",
        "> The most-connected concepts. Everything flows through these.",
        "",
    ]
    for n in god_nodes:
        doc = f" — _{n['docstring'][:100]}_" if n.get("docstring") else ""
        lines.append(f"- **{n['label']}** `{n['kind']}` ({n['project']}){doc}")

    if cross_project:
        lines += [
            "",
            "---",
            "",
            "## Cross-Project Shared Dependencies",
            "",
            "> These appear in 2+ projects — candidates for a shared package.",
            "",
        ]
        for n in cross_project:
            shared = ", ".join(n.get("shared_by", []))
            lines.append(f"- **{n['label']}** shared by: {shared}")

    if all_decisions:
        lines += [
            "",
            "---",
            "",
            "## Decisions from Claude Sessions",
            "",
            "> Extracted from your Claude Code conversation history.",
            "",
        ]
        for proj, dec in all_decisions[:15]:
            lines.append(f"- [{proj}] {dec}")

    lines += [
        "",
        "---",
        "",
        "## Suggested Questions",
        "",
        "These are questions the graph is uniquely positioned to answer:",
        "",
    ]

    if cross_project:
        dep = cross_project[0]["label"]
        lines.append(f"- What projects share `{dep}` — can it become a shared package?")
    if god_nodes:
        gn = god_nodes[0]["label"]
        lines.append(f"- What depends on `{gn}` and what would break if it changed?")
    if len(projects) > 1:
        lines.append(f"- Which patterns are consistent across {' and '.join(projects[:2])}?")
    lines.append("- What architectural decisions have been made across all projects?")
    lines.append("- Which files are mentioned most often in Claude sessions?")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
