"""Mine past failures (errors, reverts, corrections) from local Claude session logs."""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field

from coursift.sessions import CLAUDE_PROJECTS_DIR

# User-side correction / frustration signals
USER_FAILURE_SIGNALS = [
    r"\bthat (?:didn'?t|did not) work\b",
    r"\bstill (?:failing|broken|not working|errors?)\b",
    r"\b(?:revert|undo|roll ?back)\b",
    r"\bdoesn'?t work\b",
    r"\bnot working\b",
    r"\bbroke(?:n|s)?\b",
    r"\bwrong\b",
    r"\bthat'?s not (?:right|correct|what)\b",
    r"\byou (?:broke|messed up|deleted)\b",
    r"\bsame error\b",
    r"\bregression\b",
]

# Assistant-side self-correction signals
ASSISTANT_FAILURE_SIGNALS = [
    r"\byou'?re right\b",
    r"\bmy (?:mistake|apolog)",
    r"\bi (?:was wrong|made an error|introduced)\b",
    r"\bthat (?:was|is) (?:wrong|incorrect|a mistake)\b",
    r"\blet me fix\b",
    r"\bi should (?:not|n'?t) have\b",
]

_USER_RE = [re.compile(p, re.IGNORECASE) for p in USER_FAILURE_SIGNALS]
_ASSISTANT_RE = [re.compile(p, re.IGNORECASE) for p in ASSISTANT_FAILURE_SIGNALS]


@dataclass
class Lesson:
    project: str
    kind: str          # tool_error | user_correction | self_correction
    signal: str        # the matched phrase
    context: str       # surrounding text (what was being attempted)
    session: str


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                if c.get("type") == "text":
                    parts.append(c.get("text", ""))
                elif c.get("type") == "tool_result":
                    tc = c.get("content")
                    if isinstance(tc, str):
                        parts.append(tc)
                    elif isinstance(tc, list):
                        parts.extend(x.get("text", "") for x in tc if isinstance(x, dict))
        return " ".join(parts)
    return ""


def _mine_session(path: Path, project: str) -> list[Lesson]:
    lessons: list[Lesson] = []
    last_assistant_action = ""

    try:
        with path.open(encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg = d.get("message", {})
                role = msg.get("role") if isinstance(msg, dict) else None
                content = msg.get("content") if isinstance(msg, dict) else None

                # 1) tool errors (the hardest signal — something actually failed)
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("is_error"):
                            err = _text_of([c])[:200]
                            lessons.append(Lesson(
                                project=project, kind="tool_error",
                                signal="tool returned error",
                                context=f"After: {last_assistant_action[:120]} → ERROR: {err}",
                                session=path.stem,
                            ))

                text = _text_of(content)

                # remember what the assistant was doing (for context)
                if role == "assistant" and text:
                    last_assistant_action = text[:160]

                # 2) user corrections
                if role == "user" and text and not text.startswith("<"):
                    for rx in _USER_RE:
                        m = rx.search(text)
                        if m:
                            lessons.append(Lesson(
                                project=project, kind="user_correction",
                                signal=m.group(0),
                                context=f"User said: \"{text[:160]}\" (after: {last_assistant_action[:100]})",
                                session=path.stem,
                            ))
                            break

                # 3) assistant self-corrections
                if role == "assistant" and text:
                    for rx in _ASSISTANT_RE:
                        m = rx.search(text)
                        if m:
                            lessons.append(Lesson(
                                project=project, kind="self_correction",
                                signal=m.group(0),
                                context=text[:180],
                                session=path.stem,
                            ))
                            break
    except Exception:
        pass

    return lessons


def mine_lessons(projects: list[str] | None = None, limit_per_session: int = 5) -> list[Lesson]:
    """Mine failure lessons from all Claude sessions."""
    if not CLAUDE_PROJECTS_DIR.exists():
        return []

    all_lessons: list[Lesson] = []
    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        project_name = project_dir.name.split("-")[-1] or project_dir.name
        for session_file in project_dir.glob("*.jsonl"):
            found = _mine_session(session_file, project_name)
            all_lessons.extend(found[:limit_per_session])

    return all_lessons


def lessons_to_nodes_edges(lessons: list[Lesson]) -> tuple[list[dict], list[dict]]:
    """Convert lessons into graph nodes (kind='lesson')."""
    from coursift.security import redact_secrets, sanitize_for_memory

    nodes, edges = [], []
    for i, lesson in enumerate(lessons):
        nid = f"lesson::{lesson.session[:8]}::{i}"
        nodes.append({
            "id": nid,
            "label": f"⚠ {lesson.signal}",
            "kind": "lesson",
            "project": lesson.project,
            "file": "",
            "lesson_kind": lesson.kind,
            "context": redact_secrets(sanitize_for_memory(lesson.context)),
            "provenance": lesson.session,
        })
        # link lesson to its project's session node
        edges.append({
            "source": f"session::{lesson.session[:8]}",
            "target": nid,
            "relation": "learned_from_failure",
        })
    return nodes, edges
