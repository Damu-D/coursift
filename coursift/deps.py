"""Dependency audit: list third-party imports and flag unverified packages for review."""

from collections import defaultdict

from coursift.graph import load_graph

# Python standard library — derived at runtime when available (3.10+), with a
# static fallback for older interpreters. Avoids false-flagging stdlib modules.
try:
    import sys as _sys
    PY_STDLIB = set(getattr(_sys, "stdlib_module_names", set()))
except Exception:  # pragma: no cover
    PY_STDLIB = set()

PY_STDLIB |= {
    "abc", "argparse", "ast", "asyncio", "base64", "collections", "contextlib",
    "copy", "csv", "dataclasses", "datetime", "decimal", "difflib", "enum",
    "functools", "glob", "hashlib", "heapq", "hmac", "html", "http", "importlib",
    "inspect", "io", "itertools", "json", "logging", "math", "os", "pathlib",
    "pickle", "queue", "random", "re", "secrets", "shutil", "signal", "socket",
    "sqlite3", "ssl", "string", "struct", "subprocess", "sys", "tempfile",
    "textwrap", "threading", "time", "traceback", "typing", "unicodedata",
    "unittest", "urllib", "uuid", "warnings", "weakref", "xml", "zipfile",
}

# A small allowlist of widely-used packages. Real product would query PyPI/npm.
KNOWN_PACKAGES = {
    # python
    "anthropic", "openai", "requests", "httpx", "pydantic", "fastapi", "flask",
    "django", "numpy", "pandas", "scipy", "sklearn", "torch", "tensorflow",
    "typer", "click", "rich", "networkx", "sqlalchemy", "pytest", "boto3",
    "aiohttp", "uvicorn", "starlette", "tree_sitter", "tree-sitter", "mcp",
    "tiktoken", "tenacity", "tqdm", "yaml", "pyyaml", "dotenv", "redis",
    # js/ts ecosystem (bare specifiers)
    "react", "react-dom", "next", "vue", "svelte", "express", "axios", "lodash",
    "zod", "typescript", "tailwindcss", "vite", "webpack", "eslint", "prettier",
    "@anthropic-ai/sdk", "openai", "stripe", "@supabase/supabase-js", "framer-motion",
    "@sanity/client", "resend", "d3", "zustand", "swr",
}


def _normalize(module: str) -> str:
    """Top-level package name from an import string."""
    module = module.strip().strip("'\"")
    if module.startswith("."):
        return ""  # relative import — local
    # python dotted -> top level; js scoped -> keep scope
    if module.startswith("@"):
        parts = module.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else module
    return module.split("/")[0].split(".")[0]


def audit_dependencies() -> dict:
    graph = load_graph()
    if not graph:
        return {"status": "no_graph", "message": "Run `coursift build` first."}

    nodes = graph.get("nodes", [])
    # Local package names = registered project names (their own modules)
    project_names = {
        n.get("project", "").lower()
        for n in nodes if n.get("project")
    }
    per_project: dict[str, dict] = defaultdict(
        lambda: {"third_party": set(), "stdlib": set(), "local": 0, "unverified": set()}
    )

    for n in nodes:
        if n.get("kind") != "import":
            continue
        project = n.get("project", "unknown")
        top = _normalize(n.get("label", ""))
        if not top:
            per_project[project]["local"] += 1
            continue
        if top.lower() in project_names:
            per_project[project]["local"] += 1
            continue
        if top in PY_STDLIB:
            per_project[project]["stdlib"].add(top)
        elif top.lower() in {k.lower() for k in KNOWN_PACKAGES}:
            per_project[project]["third_party"].add(top)
        else:
            # Not stdlib, not in allowlist — could be local module OR slopsquat risk
            per_project[project]["unverified"].add(top)

    result = {"status": "ok", "projects": {}}
    total_unverified = 0
    for project, data in per_project.items():
        result["projects"][project] = {
            "third_party": sorted(data["third_party"]),
            "stdlib_count": len(data["stdlib"]),
            "local_imports": data["local"],
            "unverified": sorted(data["unverified"]),
        }
        total_unverified += len(data["unverified"])

    result["total_unverified"] = total_unverified
    result["note"] = (
        "Unverified = not in stdlib or the known-package allowlist. "
        "These are usually your own local modules, but ALWAYS confirm any that "
        "look like real third-party packages — slopsquat attacks register "
        "hallucinated package names as malware."
    )
    return result
