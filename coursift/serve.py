"""
Coursift MCP server — exposes the graph as live tools any agent can call.

Run:
    coursift serve              # stdio MCP server
    python -m coursift.serve

Register with Claude Code / Cursor / etc. as an MCP stdio server. Tools:
    coursift_context    — token-budgeted grounded context pack
    coursift_verify     — does this symbol exist? (anti-hallucination)
    coursift_impact     — blast radius before changing a symbol
    coursift_lessons    — past failures to avoid repeating
    coursift_preflight  — proactive briefing from current git diff
    coursift_duplicates — cross-project clone candidates

Requires the `mcp` extra:  uv tool install "coursift[mcp]"
"""

import json


def _build_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:  # pragma: no cover
        raise SystemExit(
            "The MCP server needs the 'mcp' package.\n"
            "Install with:  uv tool install \"coursift[mcp]\"   (or pip install mcp)"
        ) from e

    mcp = FastMCP("coursift")

    @mcp.tool()
    def coursift_context(question: str, max_tokens: int = 2000) -> str:
        """Grounded, token-budgeted context for a question (avoids context rot)."""
        from coursift.context_pack import build_context_pack
        return build_context_pack(question, max_tokens=max_tokens)

    @mcp.tool()
    def coursift_verify(symbol: str) -> str:
        """Check whether a function/class/file actually exists. Anti-hallucination."""
        from coursift.verify import verify_symbol
        return json.dumps(verify_symbol(symbol), indent=2)

    @mcp.tool()
    def coursift_impact(symbol: str, depth: int = 3) -> str:
        """Blast radius: what depends on this symbol before you change it."""
        from coursift.impact import blast_radius
        return json.dumps(blast_radius(symbol, max_depth=depth), indent=2)

    @mcp.tool()
    def coursift_lessons(project: str = "") -> str:
        """Past failures mined from sessions — avoid repeating these approaches."""
        from coursift.lessons import mine_lessons
        from coursift.config import list_projects
        found = mine_lessons(list_projects())
        if project:
            found = [l for l in found if project.lower() in l.project.lower()]
        return json.dumps(
            [{"project": l.project, "kind": l.kind, "signal": l.signal,
              "context": l.context[:200]} for l in found[:30]],
            indent=2,
        )

    @mcp.tool()
    def coursift_preflight(project_path: str) -> str:
        """Proactive briefing from current git diff: blast radius, coupled files, lessons."""
        from coursift.preflight import preflight
        return json.dumps(preflight(project_path), indent=2)

    @mcp.tool()
    def coursift_duplicates(threshold: float = 0.6) -> str:
        """Cross-project near-duplicate functions — candidates to extract/share."""
        from coursift.duplicates import find_duplicates, summarize
        return json.dumps(summarize(find_duplicates(threshold=threshold)), indent=2)

    @mcp.tool()
    def coursift_search(query: str, top_k: int = 10) -> str:
        """Semantic code search across all projects (local TF-IDF)."""
        from coursift.embed import TfidfIndex
        from coursift.graph import load_graph
        graph = load_graph() or {"nodes": []}
        idx, nm = TfidfIndex(), {}
        for n in graph["nodes"]:
            if n.get("kind") in ("function", "class", "file"):
                idx.add(n["id"], " ".join([n.get("label", ""), n.get("docstring", ""),
                                           " ".join(n.get("tokens", []))]))
                nm[n["id"]] = n
        idx.build()
        return json.dumps([
            {"label": nm[i].get("label"), "project": nm[i].get("project"),
             "file": nm[i].get("file"), "score": round(s, 3)}
            for i, s in idx.search(query, top_k=top_k)
        ], indent=2)

    @mcp.tool()
    def coursift_health() -> str:
        """Health & tech-debt score per project."""
        from coursift.health import health_report
        return json.dumps(health_report(), indent=2)

    return mcp


def main() -> None:
    _build_server().run()


if __name__ == "__main__":
    main()
