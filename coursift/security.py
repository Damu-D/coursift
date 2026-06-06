"""Scan memory for prompt-injection and secrets; redaction and trust scoring."""

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


# Secret patterns — detected and redacted before any text becomes memory.
SECRET_PATTERNS = [
    (r"github_pat_[A-Za-z0-9_]{20,}", "GitHub PAT"),
    (r"ghp_[A-Za-z0-9]{36,}", "GitHub token"),
    (r"gho_[A-Za-z0-9]{36,}", "GitHub OAuth token"),
    (r"sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}", "API secret key"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"AIza[0-9A-Za-z_-]{35}", "Google API key"),
    (r"xox[baprs]-[0-9A-Za-z-]{10,}", "Slack token"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "Private key"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT"),
    (r"postgres(?:ql)?://[^\s:]+:[^\s@]+@", "Postgres URL with password"),
]
_SECRET_RE = [(re.compile(p), label) for p, label in SECRET_PATTERNS]


def detect_secrets(text: str) -> list[str]:
    """Return labels of any secrets found (never the secret itself)."""
    found = []
    for rx, label in _SECRET_RE:
        if rx.search(text):
            found.append(label)
    return found


def redact_secrets(text: str) -> str:
    """Replace any detected secret with a [REDACTED:label] marker."""
    out = text
    for rx, label in _SECRET_RE:
        out = rx.sub(f"[REDACTED:{label}]", out)
    return out


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

    secrets = detect_secrets(text)
    for label in secrets:
        findings.append(f"secret:{label}")

    # trust score: 1.0 clean -> lower as findings accumulate
    trust = max(0.0, 1.0 - 0.34 * len(findings))
    level = "clean" if trust >= 0.9 else "suspect" if trust >= 0.5 else "poisoned"

    return {
        "trust": round(trust, 2),
        "level": level,
        "findings": findings[:10],
        "has_hidden_unicode": hidden,
        "secrets": secrets,
    }


def sanitize_for_memory(text: str) -> str:
    """Strip hidden control chars AND redact secrets before text becomes memory."""
    cleaned = "".join(
        ch for ch in text
        if not (unicodedata.category(ch) in ("Cf",) or ch in "‪‫‬‭‮")
    )
    return redact_secrets(cleaned)


def audit_graph(graph: dict) -> dict:
    """Scan all session/doc-derived memory in a graph for poisoning."""
    nodes = graph.get("nodes", [])
    flagged = []
    scanned = 0
    for n in nodes:
        if n.get("kind") not in ("session", "concept", "lesson"):
            continue
        scanned += 1
        blob = " ".join([
            n.get("label", ""),
            n.get("context", ""),
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
