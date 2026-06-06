"""Index Claude Code session logs into memory nodes with provenance and trust scoring."""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


@dataclass
class SessionEntry:
    session_id: str
    project_path: str
    project_name: str
    messages: list[dict] = field(default_factory=list)
    file_mentions: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    timestamp: str = ""


_FILE_RE = re.compile(r"(?:src/|app/|lib/|components/|api/)[\w/\-\.]+\.\w+")
_DECISION_RE = re.compile(
    r"(?:we (?:decided|chose|agreed|will use|are using)|"
    r"the (?:approach|pattern|solution|fix) is|"
    r"instead of|switched to|moved to|refactored)",
    re.IGNORECASE,
)


def _extract_file_mentions(text: str) -> list[str]:
    return list({m.group() for m in _FILE_RE.finditer(text)})


def _extract_decisions(messages: list[dict]) -> list[str]:
    decisions = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
            )
        if isinstance(content, str) and _DECISION_RE.search(content):
            # Extract the sentence containing the decision keyword
            for sentence in content.split(". "):
                if _DECISION_RE.search(sentence):
                    decisions.append(sentence.strip()[:300])
    return decisions[:20]  # cap at 20 per session


def _extract_concepts(messages: list[dict]) -> list[str]:
    """Pull out capitalized terms and code identifiers that appear repeatedly."""
    all_text = ""
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
            )
        if isinstance(content, str):
            all_text += content + " "

    # camelCase, PascalCase, or backtick-wrapped identifiers
    identifiers = re.findall(r"`([^`]+)`|(?<!\w)([A-Z][a-zA-Z]{2,}(?:[A-Z][a-z]+)*)", all_text)
    flat = [i[0] or i[1] for i in identifiers if (i[0] or i[1])]

    # Count frequency and return top ones
    from collections import Counter
    counter = Counter(flat)
    return [term for term, count in counter.most_common(15) if count >= 2]


def index_sessions(registered_projects: list[str] | None = None) -> list[SessionEntry]:
    """
    Read all Claude Code session files and extract structured info.
    If registered_projects is provided, only index sessions for those paths.
    """
    if not CLAUDE_PROJECTS_DIR.exists():
        return []

    entries: list[SessionEntry] = []

    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        # The dir name is a URL-encoded or dash-encoded project path
        project_path = project_dir.name.replace("-", "/")
        # Try to match against registered projects
        if registered_projects:
            matched = any(
                rp.replace("/", "-") in project_dir.name or project_dir.name in rp.replace("/", "-")
                for rp in registered_projects
            )
            if not matched:
                # Still include it but mark as unregistered
                pass

        project_name = project_dir.name.split("-")[-1] if "-" in project_dir.name else project_dir.name

        # Read session JSON files
        for session_file in project_dir.glob("*.jsonl"):
            try:
                messages = []
                with session_file.open(encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                messages.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

                if not messages:
                    continue

                all_text = ""
                for msg in messages:
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        content = " ".join(
                            c.get("text", "") for c in content
                            if isinstance(c, dict) and c.get("type") == "text"
                        )
                    if isinstance(content, str):
                        all_text += content + " "

                entry = SessionEntry(
                    session_id=session_file.stem,
                    project_path=str(project_dir),
                    project_name=project_name,
                    messages=messages[:5],  # store first 5 messages only (memory efficient)
                    file_mentions=_extract_file_mentions(all_text),
                    decisions=_extract_decisions(messages),
                    concepts=_extract_concepts(messages),
                    timestamp=str(session_file.stat().st_mtime),
                )
                entries.append(entry)

            except Exception:
                continue

    return entries


def sessions_to_nodes_edges(entries: list[SessionEntry]) -> tuple[list[dict], list[dict]]:
    """
    Convert session entries into graph nodes and edges.
    Each memory node carries provenance (source + timestamp) and a trust score
    from injection scanning — OWASP-recommended for poison-resistant memory.
    """
    from coursift.security import scan_text, sanitize_for_memory

    nodes, edges = [], []

    for entry in entries:
        session_node_id = f"session::{entry.session_id[:8]}"
        clean_decisions = [sanitize_for_memory(d) for d in entry.decisions[:5]]
        scan = scan_text(" ".join(clean_decisions + entry.concepts[:10]))
        nodes.append({
            "id": session_node_id,
            "label": f"Session ({entry.project_name})",
            "kind": "session",
            "project": entry.project_name,
            "file": entry.project_path,
            "decisions": clean_decisions,
            "concepts": entry.concepts[:10],
            # provenance + trust (anti memory-poisoning)
            "provenance": entry.session_id,
            "timestamp": entry.timestamp,
            "trust": scan["trust"],
            "trust_level": scan["level"],
        })

        for concept in entry.concepts:
            concept_id = f"concept::{concept.lower()}"
            nodes.append({
                "id": concept_id,
                "label": concept,
                "kind": "concept",
                "project": entry.project_name,
                "file": "",
            })
            edges.append({
                "source": session_node_id,
                "target": concept_id,
                "relation": "references",
            })

        for file_mention in entry.file_mentions[:10]:
            edges.append({
                "source": session_node_id,
                "target": f"file::{file_mention}",
                "relation": "mentions",
            })

    return nodes, edges
