"""
Temporal Coupling — files that change together, mined from git history.

Solves (2026 problem):
  Impact tools uncover "hidden temporal relationships where files frequently
  change together." These couplings are invisible to static analysis: two files
  with no import between them but that always change in the same commit are
  logically coupled. An agent editing one should check the other.

`coursift coupling` mines git commit history across projects and reports the
strongest co-change pairs (support + confidence), then adds them to the graph
as `co_change` edges.

Uses git locally. No API.
"""

import subprocess
from collections import defaultdict
from itertools import combinations
from pathlib import Path

CODE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java",
    ".rb", ".cs", ".swift", ".sql", ".vue", ".svelte",
}


def _git_commits(project: str, max_commits: int = 400) -> list[list[str]]:
    """Return a list of commits, each a list of changed code files."""
    try:
        out = subprocess.run(
            ["git", "-C", project, "log", f"-{max_commits}",
             "--name-only", "--pretty=format:===%H"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode != 0:
            return []
    except Exception:
        return []

    commits, current = [], []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith("==="):
            if current:
                commits.append(current)
            current = []
        elif line and Path(line).suffix.lower() in CODE_SUFFIXES:
            current.append(line)
    if current:
        commits.append(current)
    return commits


def detect_coupling(project: str, min_support: int = 3, min_confidence: float = 0.6) -> list[dict]:
    """
    Find file pairs that change together.
      support    = number of commits where BOTH changed
      confidence = support / (commits where the more-rarely-changed file changed)
    """
    commits = _git_commits(project)
    if not commits:
        return []

    file_count: dict[str, int] = defaultdict(int)
    pair_count: dict[tuple[str, str], int] = defaultdict(int)

    for files in commits:
        unique = sorted(set(files))
        if len(unique) > 40:   # skip giant mechanical commits (formatting, deps)
            continue
        for f in unique:
            file_count[f] += 1
        for a, b in combinations(unique, 2):
            pair_count[(a, b)] += 1

    results = []
    for (a, b), support in pair_count.items():
        if support < min_support:
            continue
        denom = min(file_count[a], file_count[b])
        confidence = support / denom if denom else 0
        if confidence >= min_confidence:
            results.append({
                "project": Path(project).name,
                "file_a": a,
                "file_b": b,
                "support": support,
                "confidence": round(confidence, 2),
            })

    results.sort(key=lambda r: (r["support"], r["confidence"]), reverse=True)
    return results


def detect_all(projects: list[str]) -> list[dict]:
    all_pairs = []
    for p in projects:
        if Path(p).exists():
            all_pairs.extend(detect_coupling(p))
    return all_pairs


def coupling_to_edges(pairs: list[dict]) -> list[dict]:
    """Convert co-change pairs into graph edges (file-level)."""
    edges = []
    for pr in pairs:
        edges.append({
            "source": f"file::{pr['file_a']}",
            "target": f"file::{pr['file_b']}",
            "relation": "co_change",
            "support": pr["support"],
            "confidence": pr["confidence"],
        })
    return edges
