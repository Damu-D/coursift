"""
Preflight — proactive, predictive briefing BEFORE you start coding.

Implements the 2026→2027 "proactive agent" direction: "agents initiate based on
learned patterns and contextual cues rather than awaiting explicit prompts."

Given your current uncommitted changes (git diff), `coursift preflight` assembles
a briefing WITHOUT being asked what to look at:
  1. Blast radius of the symbols you're touching
  2. Coupled files you should probably also edit (from git co-change history)
  3. Past failure lessons relevant to these files
  4. Established decisions for this project

It turns "the agent starts from zero" into "the agent walks in already briefed."

100% local, no API.
"""

import subprocess
from pathlib import Path

from coursift.graph import load_graph
from coursift.coupling import detect_coupling
from coursift.lessons import mine_lessons


def _changed_files(project: str) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", project, "status", "--porcelain"],
            capture_output=True, text=True, timeout=15,
        )
        files = []
        for line in out.stdout.splitlines():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                files.append(parts[1])
        return files
    except Exception:
        return []


def preflight(project: str) -> dict:
    project = str(Path(project).expanduser().resolve())
    name = Path(project).name
    changed = _changed_files(project)
    if not changed:
        return {"status": "clean", "project": name,
                "message": "No uncommitted changes — nothing to brief."}

    graph = load_graph()
    nodes = graph.get("nodes", []) if graph else []
    edges = graph.get("edges", []) if graph else []

    # 1) symbols defined in changed files + their dependents (blast radius)
    changed_basenames = {Path(c).name for c in changed}
    touched_nodes = [
        n for n in nodes
        if Path(n.get("file", "")).name in changed_basenames
        and n.get("kind") in ("function", "class")
    ]
    dependents: dict[str, list[str]] = {}
    for e in edges:
        dependents.setdefault(e["target"], []).append(e["source"])
    node_by_id = {n["id"]: n for n in nodes}
    impacted = set()
    for tn in touched_nodes:
        for dep in dependents.get(tn["id"], []):
            d = node_by_id.get(dep)
            if d and Path(d.get("file", "")).name not in changed_basenames:
                impacted.add((d.get("label"), d.get("project"), Path(d.get("file", "")).name))

    # 2) coupled files (from git history) for the changed files
    coupling = detect_coupling(project, min_support=2, min_confidence=0.5)
    best_by_file: dict[str, tuple[int, float]] = {}
    for pair in coupling:
        a, b = Path(pair["file_a"]).name, Path(pair["file_b"]).name
        other = None
        if a in changed_basenames and b not in changed_basenames:
            other = b
        elif b in changed_basenames and a not in changed_basenames:
            other = a
        if other:
            cur = best_by_file.get(other)
            cand = (pair["support"], pair["confidence"])
            if cur is None or cand > cur:
                best_by_file[other] = cand
    coupled_suggestions = sorted(
        ((f, s, c) for f, (s, c) in best_by_file.items()),
        key=lambda x: (-x[1], -x[2]),
    )[:8]

    # 3) relevant failure lessons for this project
    lessons = [l for l in mine_lessons([project]) if name.lower() in l.project.lower()]

    # 4) established decisions for this project
    decisions = []
    for n in nodes:
        if n.get("kind") == "session" and name.lower() in str(n.get("project", "")).lower():
            decisions.extend(n.get("decisions", [])[:3])

    return {
        "status": "ok",
        "project": name,
        "changed_files": changed,
        "blast_radius": sorted(impacted)[:15],
        "also_edit": coupled_suggestions,
        "relevant_lessons": [(l.kind, l.signal, l.context[:120]) for l in lessons[:6]],
        "decisions": list(dict.fromkeys(decisions))[:5],
    }
