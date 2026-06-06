"""Config management — stores registered projects and global settings."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".coursift"
CONFIG_FILE = CONFIG_DIR / "config.json"
GRAPH_FILE = CONFIG_DIR / "graph.json"
SESSIONS_FILE = CONFIG_DIR / "sessions.json"
CACHE_DIR = CONFIG_DIR / "cache"


def _defaults() -> dict:
    return {
        "projects": [],
        "anthropic_model": "claude-opus-4-5",
        "version": "0.1.0",
    }


def load() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save(_defaults())
    with CONFIG_FILE.open() as f:
        return json.load(f)


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w") as f:
        json.dump(cfg, f, indent=2)


def add_project(path: str) -> tuple[bool, str]:
    """Register a project. Returns (added, message)."""
    resolved = str(Path(path).expanduser().resolve())
    if not Path(resolved).exists():
        return False, f"Path does not exist: {resolved}"
    cfg = load()
    if resolved in cfg["projects"]:
        return False, f"Already registered: {resolved}"
    cfg["projects"].append(resolved)
    save(cfg)
    return True, resolved


def remove_project(path: str) -> tuple[bool, str]:
    resolved = str(Path(path).expanduser().resolve())
    cfg = load()
    if resolved not in cfg["projects"]:
        return False, f"Not registered: {resolved}"
    cfg["projects"].remove(resolved)
    save(cfg)
    return True, resolved


def list_projects() -> list[str]:
    return load().get("projects", [])
