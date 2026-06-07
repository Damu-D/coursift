"""Project scoping: focus commands on the project you're working in."""

import os
from pathlib import Path

from coursift.config import list_projects


def active_project_from_cwd(cwd: str | None = None) -> str | None:
    """Return the registered project name whose path contains the cwd, if any."""
    here = Path(cwd or os.getcwd()).resolve()
    best: tuple[int, str] | None = None
    for path in list_projects():
        p = Path(path).resolve()
        try:
            here.relative_to(p)
        except ValueError:
            continue
        # most specific (longest) matching path wins
        depth = len(p.parts)
        if best is None or depth > best[0]:
            best = (depth, p.name)
    return best[1] if best else None


def resolve_scope(project_flag: str | None, all_flag: bool) -> tuple[set[str] | None, str]:
    """
    Decide which projects a command should look at.

    Returns (project_names | None, label):
      - explicit --project   -> just that project
      - --all                -> None (no filter; every project)
      - otherwise            -> auto-detect from cwd; falls back to all
    """
    if all_flag:
        return None, "all projects"
    if project_flag:
        return {project_flag.lower()}, project_flag
    auto = active_project_from_cwd()
    if auto:
        return {auto.lower()}, f"{auto} (auto-detected)"
    return None, "all projects"


def in_scope(node: dict, scope: set[str] | None) -> bool:
    """True if a node belongs to the scoped project set (None = everything)."""
    if scope is None:
        return True
    return node.get("project", "").lower() in scope
