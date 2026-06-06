"""
Memory-poisoning / prompt-injection scanner + provenance trust scoring.

Solves (2026 problems):
  - Memory poisoning: malicious instructions written into an agent's persistent
    memory re-emerge on every invocation (MINJA: >95% success; AgentPoison:
    >80% at <0.1% poison rate).
  - Indirect prompt injection via poisoned data sources.

Before any session/doc text becomes "memory" the agent trusts, Coursift scans
it for injection markers, assigns a trust score, and tags provenance.
OWASP-recommended: input moderation + provenance tracking + trust-aware retrieval.

Local heuristics (regex + unicode checks). No API.
"""

import re
import unicodedata

# Common prompt-injection / jailbreak markers.
INJECTION_PATTERNS = [
    r"ignore (?:all |the )?(?:previous|prior|above) (?:instructions|prompts)",
    r"disregard (?:all |the )?(?:previous|prior|above)",
    r"forget (?:everything|all|your) (?:instructions|rules|context)",
    r"you are now (?:a|an|in)\b",
    r"new (?:instructions|system prompt|directive)s?:",
    r"system prompt\s*[:=]",
    r"do not (?:tell|inform|warn) the user",
    r"<\s*(?:system|im_start|im_end)\s*>",
    r"\bDAN\b mode",
    r"act as (?:if you are )?(?:an? )?(?:unrestricted|jailbroken)",
    r"(?:exfiltrate|leak|send).{0,30}(?:api[_ ]?key|secret|token|password)",
    r"reveal your (?:system )?(?:prompt|instructions)",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def _has_hidden_unicode(text: str) -> bool:
    """Detect zero-width / bidi-control chars used to hide injected instructions."""
    suspicious = {
        "​", "‌", "‍", "⁠",  # zero-width
        "‪", "‫", "‬", "‭", "‮",  # bidi overrides
        "﻿",
    }
    return any(ch in suspicious for ch in text)


def scan_text(text: str) -> dict:
    """Scan a blob of text for injection markers. Returns findings + trust score."""
    findings = []
    for pat in _COMPILED:
        m = pat.search(text)
        if m:
            findings.append(m.group(0)[:80])

    hidden = _has_hidden_unicode(text)
    if hidden:
        findings.append("hidden-unicode-control-chars")

    # trust score: 1.0 clean -> lower as findings accumulate
    trust = max(0.0, 1.0 - 0.34 * len(findings))
    level = "clean" if trust >= 0.9 else "suspect" if trust >= 0.5 else "poisoned"

    return {
        "trust": round(trust, 2),
        "level": level,
        "findings": findings[:10],
        "has_hidden_unicode": hidden,
    }


def sanitize_for_memory(text: str) -> str:
    """Strip hidden control chars before text enters the graph as memory."""
    cleaned = "".join(
        ch for ch in text
        if not (unicodedata.category(ch) in ("Cf",) or ch in "‪‫‬‭‮")
    )
    return cleaned


def audit_graph(graph: dict) -> dict:
    """Scan all session/doc-derived memory in a graph for poisoning."""
    nodes = graph.get("nodes", [])
    flagged = []
    scanned = 0
    for n in nodes:
        if n.get("kind") not in ("session", "concept"):
            continue
        scanned += 1
        blob = " ".join([
            n.get("label", ""),
            " ".join(n.get("decisions", []) or []),
            " ".join(n.get("concepts", []) or []),
        ])
        result = scan_text(blob)
        if result["level"] != "clean":
            flagged.append({
                "node": n.get("label"),
                "project": n.get("project"),
                **result,
            })

    return {
        "scanned": scanned,
        "flagged": flagged,
        "status": "clean" if not flagged else "warnings",
        "summary": (
            f"Scanned {scanned} memory nodes — all clean."
            if not flagged else
            f"⚠ {len(flagged)} memory node(s) show injection markers. "
            f"These were extracted from sessions/docs and could poison agent memory."
        ),
    }
