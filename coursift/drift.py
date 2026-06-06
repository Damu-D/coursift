"""Documentation drift detector: flag code changed without matching doc updates (via git)."""

import subprocess
from pathlib import Path

CODE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".go", ".rs",
    ".java", ".rb", ".cs", ".swift", ".sql",
}
DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt"}
DOC_NAMES = {"readme", "changelog", "agents", "claude", "contributing"}


def _git(project: str, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", project, *args],
            capture_output=True, text=True, timeout=20,
        )
        return out.stdout if out.returncode == 0 else ""
    except Exception:
        return ""


def _is_git_repo(project: str) -> bool:
    return bool(_git(project, "rev-parse", "--is-inside-work-tree").strip())


def detect_drift(project: str, days: int = 30) -> dict:
    """Detect doc drift in one project over the last `days` days."""
    if not _is_git_repo(project):
        return {"project": Path(project).name, "status": "not_git"}

    since = f"--since={days}.days.ago"
    log = _git(project, "log", since, "--name-only", "--pretty=format:%H")
    if not log:
        return {"project": Path(project).name, "status": "no_recent_commits"}

    code_changed: set[str] = set()
    docs_changed: set[str] = set()
    for line in log.splitlines():
        line = line.strip()
        if not line or len(line) == 40 and all(c in "0123456789abcdef" for c in line):
            continue  # commit hash line
        p = Path(line)
        suffix = p.suffix.lower()
        stem = p.stem.lower()
        if suffix in CODE_SUFFIXES:
            code_changed.add(line)
        elif suffix in DOC_SUFFIXES or stem in DOC_NAMES:
            docs_changed.add(line)

    drift = len(code_changed) > 0 and len(docs_changed) == 0
    return {
        "project": Path(project).name,
        "status": "drift" if drift else "ok",
        "days": days,
        "code_files_changed": len(code_changed),
        "doc_files_changed": len(docs_changed),
        "sample_code": sorted(code_changed)[:8],
        "message": (
            f"⚠ {len(code_changed)} code files changed in {days}d but NO docs were "
            f"updated. Docs may be stale — AI will generate from outdated specs."
            if drift else
            f"✓ {len(code_changed)} code / {len(docs_changed)} doc files changed — "
            f"docs are being maintained."
        ),
    }


def detect_all(projects: list[str], days: int = 30) -> list[dict]:
    return [detect_drift(p, days) for p in projects if Path(p).exists()]
