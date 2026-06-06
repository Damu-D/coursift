"""
Code scanner — extracts nodes (files, functions, classes, imports) from projects.
Uses Python's ast module for .py files and regex for TS/JS/TSX files.
tree-sitter support planned for v2.
"""

import ast
import re
import hashlib
from pathlib import Path
from dataclasses import dataclass, field

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".next", "dist", "build",
    ".turbo", "coverage", ".cache", "graphify-out", "coursift-out",
    ".claude", "venv", ".venv", "env", "site-packages", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "vendor",
    "target", ".gradle", ".idea", ".vscode", "out", ".output",
}


def _is_ignored_dir(part: str) -> bool:
    """Skip known dirs, any hidden dir, and anything that looks like a venv."""
    if part in IGNORE_DIRS:
        return True
    if part.startswith(".") and part not in {".", ".."}:
        return True  # hidden dirs (.venv-test, .anything)
    if part.endswith(("-env", "-venv", ".egg-info")):
        return True
    return False

CODE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".rb", ".cs", ".swift",
    ".sql", ".sh", ".bash",
}

DOC_EXTENSIONS = {".md", ".mdx", ".txt", ".rst", ".yaml", ".yml", ".json"}


@dataclass
class Node:
    id: str
    label: str
    kind: str        # file | function | class | import | concept
    project: str
    file: str
    line: int = 0
    docstring: str = ""
    tags: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)  # body identifier tokens (clone detection)


@dataclass
class Edge:
    source: str
    target: str
    relation: str    # imports | calls | defines | references | inherits


def _node_id(project: str, file: str, name: str) -> str:
    raw = f"{project}::{file}::{name}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _body_tokens(node, cap: int = 40) -> list[str]:
    """Identifier tokens used inside a function/class body (for clone detection)."""
    toks: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            toks.add(child.id)
        elif isinstance(child, ast.Attribute):
            toks.add(child.attr)
        elif isinstance(child, ast.arg):
            toks.add(child.arg)
        elif isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            toks.add(child.func.id)
    # drop trivial 1-char names; keep deterministic order
    cleaned = sorted(t for t in toks if len(t) > 1)
    return cleaned[:cap]


def _scan_python(path: Path, project: str) -> tuple[list[Node], list[Edge]]:
    nodes, edges = [], []
    rel = str(path)
    file_id = _node_id(project, rel, "__file__")
    nodes.append(Node(id=file_id, label=path.name, kind="file", project=project, file=rel))

    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return nodes, edges

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node) or ""
            nid = _node_id(project, rel, node.name)
            nodes.append(Node(
                id=nid, label=node.name, kind="function",
                project=project, file=rel, line=node.lineno, docstring=doc[:200],
                tokens=_body_tokens(node),
            ))
            edges.append(Edge(source=file_id, target=nid, relation="defines"))

        elif isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or ""
            nid = _node_id(project, rel, node.name)
            nodes.append(Node(
                id=nid, label=node.name, kind="class",
                project=project, file=rel, line=node.lineno, docstring=doc[:200],
                tokens=_body_tokens(node),
            ))
            edges.append(Edge(source=file_id, target=nid, relation="defines"))

        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module = ""
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
            else:
                module = node.module or ""
            if module:
                iid = _node_id(project, rel, f"import::{module}")
                nodes.append(Node(
                    id=iid, label=module, kind="import",
                    project=project, file=rel, line=node.lineno,
                ))
                edges.append(Edge(source=file_id, target=iid, relation="imports"))

    return nodes, edges


# Regex patterns for TypeScript/JavaScript
_TS_FUNCTION = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+(\w+)|"
    r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(",
    re.MULTILINE,
)
_TS_CLASS = re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE)
_TS_IMPORT = re.compile(r"(?:import|require)\s*[\({'\"]([^'\"\)]+)['\"\))]", re.MULTILINE)
_TS_INTERFACE = re.compile(r"(?:export\s+)?interface\s+(\w+)", re.MULTILINE)
_TS_TYPE = re.compile(r"(?:export\s+)?type\s+(\w+)\s*=", re.MULTILINE)


def _scan_ts_js(path: Path, project: str) -> tuple[list[Node], list[Edge]]:
    nodes, edges = [], []
    rel = str(path)
    file_id = _node_id(project, rel, "__file__")
    nodes.append(Node(id=file_id, label=path.name, kind="file", project=project, file=rel))

    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return nodes, edges

    for m in _TS_FUNCTION.finditer(source):
        name = m.group(1) or m.group(2)
        if name:
            nid = _node_id(project, rel, name)
            line = source[: m.start()].count("\n") + 1
            body = source[m.start(): m.start() + 600]
            toks = sorted({t for t in re.findall(r"[A-Za-z_]\w+", body) if len(t) > 1})[:40]
            nodes.append(Node(id=nid, label=name, kind="function", project=project,
                              file=rel, line=line, tokens=toks))
            edges.append(Edge(source=file_id, target=nid, relation="defines"))

    for m in _TS_CLASS.finditer(source):
        name = m.group(1)
        nid = _node_id(project, rel, f"class::{name}")
        line = source[: m.start()].count("\n") + 1
        nodes.append(Node(id=nid, label=name, kind="class", project=project, file=rel, line=line))
        edges.append(Edge(source=file_id, target=nid, relation="defines"))

    for m in _TS_INTERFACE.finditer(source):
        name = m.group(1)
        nid = _node_id(project, rel, f"interface::{name}")
        line = source[: m.start()].count("\n") + 1
        nodes.append(Node(id=nid, label=name, kind="class", project=project, file=rel, line=line, tags=["interface"]))
        edges.append(Edge(source=file_id, target=nid, relation="defines"))

    for m in _TS_IMPORT.finditer(source):
        module = m.group(1).strip()
        if module:
            iid = _node_id(project, rel, f"import::{module}")
            nodes.append(Node(id=iid, label=module, kind="import", project=project, file=rel))
            edges.append(Edge(source=file_id, target=iid, relation="imports"))

    return nodes, edges


def scan_project(project_path: str) -> tuple[list[Node], list[Edge]]:
    """Scan a single project directory and return all nodes + edges."""
    root = Path(project_path)
    project_name = root.name
    all_nodes: list[Node] = []
    all_edges: list[Edge] = []

    # Build relative parts check so we only inspect parts under the project root
    root_parts = len(root.parts)

    for path in root.rglob("*"):
        # Skip ignored dirs (only check parts below the project root)
        if any(_is_ignored_dir(part) for part in path.parts[root_parts:]):
            continue
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        if suffix == ".py":
            n, e = _scan_python(path, project_name)
        elif suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
            n, e = _scan_ts_js(path, project_name)
        else:
            continue

        all_nodes.extend(n)
        all_edges.extend(e)

    return all_nodes, all_edges
