<div align="center">
  <h1>Coursift</h1>
  <p><strong>Cross-project knowledge graph and memory layer for AI coding agents.</strong></p>
  <p>Maps your code, AI conversations, and decisions across <em>all</em> your projects — not just one.</p>
  <p>📖 New here? Read <a href="docs/WHAT_IS_COURSIFT.md"><strong>What is Coursift?</strong></a> for a plain-English overview.</p>

  <a href="https://pypi.org/project/coursift/"><img src="https://img.shields.io/pypi/v/coursift?color=7c3aed" alt="PyPI"/></a>
  <a href="https://github.com/Damu-D/coursift/actions"><img src="https://github.com/Damu-D/coursift/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <img src="https://img.shields.io/badge/Claude%20Code-skill-a78bfa?logo=anthropic&logoColor=white" alt="Claude Code skill"/>
  <img src="https://img.shields.io/pypi/pyversions/coursift" alt="Python versions"/>
</div>

---

## What is Coursift?

Every developer has multiple projects. AI assistants today only understand *one project at a time* — and they have no memory of *why* you built things.

Coursift fixes both.

```
coursift add ~/projects/myapp
coursift add ~/projects/api-service
coursift add ~/projects/design-system
coursift build
coursift query "which projects share the same auth pattern?"
```

You get:
- A **unified knowledge graph** across all your codebases
- **Session memory** — Claude's past decisions and context extracted from `~/.claude/projects/`
- **Cross-project links** — shared dependencies, repeated patterns, candidates for extraction
- An **interactive browser visualization** you can filter and explore
- A **Claude Code skill** that installs once and works in every session

---

## The 2026 AI problems Coursift is built to solve

AI coding tools in 2026 share a well-documented set of failures. Coursift attacks each one with a concrete, **local-first** command — no token-burning, no black box.

| 2026 problem | What goes wrong | Coursift's answer |
|---|---|---|
| **Context rot** | Agents degrade after ~1h as the window fills with noise; forget signatures they wrote | `coursift context` — token-budgeted, relevance-ranked grounded subgraph instead of whole files |
| **Hallucinated APIs** | Models invent functions/methods that don't exist | `coursift verify <symbol>` — confirms a symbol is real or returns closest matches |
| **Slopsquatting** | ~20% of AI code imports packages that don't exist; attackers pre-register them as malware | `coursift deps` — flags unverified third-party imports for review |
| **Lost in the middle / cost** | Big context windows bury key facts and cost a fortune | Token-budgeted context packs (GraphRAG-style anchor + 1-hop neighbors) |
| **Memory poisoning** | Injected instructions persist in agent memory (MINJA: >95% success) | `coursift audit` + provenance & trust scoring on every memory node |
| **Doc drift** | Code changes, docs don't → agents code from stale specs | `coursift drift` — flags code-changed-but-docs-didn't via git |
| **Selective forgetting** | Memory systems bloat; "most fail at forgetting" | `coursift forget 90d` + recency decay weighting |
| **No codebase awareness** | #1 developer ask; single-file assistants are obsolete | Unified multi-project graph + session memory |

> GraphRAG-style grounding (knowledge graph → retrieval) is the 2026 standard and cuts hallucination **40–62%**. Coursift brings it to your whole workspace, locally.

---

## Frontier features — things no other personal tool does yet

These target *open* problems flagged in 2026 research as still unsolved:

| Capability | The unsolved problem it attacks | Command |
|---|---|---|
| **Failure memory** | Agents repeat approaches that already failed ("hallucination loops"). Research: extract lessons *from failures*. Coursift mines **your own Claude session logs** for errors, reverts, and corrections. | `coursift lessons` |
| **Blast radius** | "Agents start from zero and modify components without checking what depends on them." Coursift walks reverse edges to show transitive dependents — **across projects** — before you change anything. | `coursift impact <symbol>` |
| **Temporal coupling** | Files that always change together but have no import between them — invisible to static analysis. Mined from git history. | `coursift coupling` |
| **Secret-leak defense** | Conversation memory captures pasted credentials (data-exfiltration surface). Coursift detects & **redacts secrets on write**, and scans existing memory. | `coursift secrets` |

> The OSS "agent memory race" of 2026 concluded the one missing system is one that does **both** a codebase-aware graph *and* conversation memory "without a compiler toolchain." That is exactly what Coursift is — pure-Python, local, no toolchain.

---

## Self-evolving layer (v0.4) — memory that gets *wiser*, not just bigger

Implements 2026→2027 frontier research (ReMe, ReasoningBank, Policy-as-Prompt, proactive agents):

| Capability | Frontier idea it implements | Command |
|---|---|---|
| **Memory consolidation** | ReMe's "sleep cycle": distill raw failures into higher-order **insights**, dedupe concepts, prune trivia — the graph gets wiser over time. | `coursift consolidate` |
| **Learned constitution** | ReasoningBank + Policy-as-Prompt: auto-write a `CONSTITUTION.md` of guardrails **distilled from your real failures**, per project. | `coursift constitution` |
| **Proactive preflight** | "Agents act on cues, not prompts": from your current git diff, brief the agent on blast radius + coupled files + past failures **before** it codes. | `coursift preflight` |
| **Semantic code search** | Hybrid GraphRAG: local TF-IDF + graph, no API, no embeddings server. | `coursift search` |
| **Cross-project clone detection** | Embedding-style duplicate detection across repos — find logic to extract into a shared package. | `coursift duplicates` |
| **Live MCP tools** | Expose `context`/`verify`/`impact`/`lessons`/`preflight`/`duplicates` as MCP tools any agent calls mid-session. | `coursift serve` |

> Everything is **pure-Python and local** — no numpy, no torch, no embeddings API. The semantic engine is a hand-rolled TF-IDF + Jaccard index that runs offline on any machine.

---

## Insight layer (v0.5) — understand, cost, and grade your whole workspace

| Capability | Problem it solves | Command |
|---|---|---|
| **Onboarding generator** | Devs spend ~58% of time on comprehension; onboarding takes ~6 weeks. Auto-writes a "start here" tour: stack, entry points, reading order, the *why*. | `coursift onboard <project>` |
| **Cost observability** | Agents use 5–30× more tokens; only 39% of orgs can attribute spend. Rolls up real token spend per project from session telemetry. | `coursift cost` |
| **Health & tech-debt score** | Tech debt costs $2.4T/yr; AI error rates rise 2–5× on unhealthy code. One 0–100 score per project from coupling, duplicates, failure density, comprehension debt. | `coursift health` |

---

## How it's different

Most code-graph tools map a **single repository's code**. Coursift goes wider and deeper: it spans **all your projects at once**, remembers **why** code exists by reading your past AI sessions, and adds a grounding + safety + self-evolving-memory layer on top. If you've seen tools like Graphify, think of Coursift as that idea taken several steps further — but it stands on its own.

---

## Works with every AI coding agent

Coursift installs instructions in the formats each tool reads — so whatever you use, it knows how to query the graph:

```bash
coursift install --platform all       # write configs for every platform
coursift install --platform cursor    # or just one
```

Supported: **Claude Code, Cursor, GitHub Copilot, Codex, Gemini CLI, Windsurf, Cline, OpenCode, Zed, Aider** — plus the universal **`AGENTS.md`** standard that 20+ other agents read natively.

---

## Install

```bash
# Recommended
uv tool install coursift

# Or
pipx install coursift
pip install coursift
```

**Register your projects and build:**
```bash
coursift add ~/projects/myapp
coursift add ~/projects/other-service
coursift build
```

**Install the Claude Code skill (once, globally):**
```bash
coursift install
```

---

## Commands

| Command | What it does |
|---|---|
| `coursift add <path>` | Register a project |
| `coursift remove <path>` | Unregister a project |
| `coursift list` | List registered projects |
| `coursift build` | Build the unified graph |
| `coursift query "<question>"` | Ask a question (LLM, uses the graph) |
| `coursift context "<q>" -t 2000` | Token-budgeted grounded context pack (local) |
| `coursift verify <symbol>` | Anti-hallucination: does this symbol exist? |
| `coursift deps` | Dependency / slopsquat audit |
| `coursift drift --days 30` | Documentation drift detector |
| `coursift audit` | Memory-poisoning / injection scan |
| `coursift forget 90d` | Prune stale memory (selective forgetting) |
| `coursift lessons` | Failure memory mined from your sessions |
| `coursift impact <symbol>` | Blast radius — what depends on this |
| `coursift coupling` | Files that change together (git) |
| `coursift secrets` | Scan memory for leaked credentials |
| `coursift search "<q>"` | Semantic code search (local, no API) |
| `coursift duplicates` | Cross-project clone detection |
| `coursift consolidate` | Distill failures → insights ("sleep cycle") |
| `coursift constitution` | Auto-generate learned guardrails |
| `coursift preflight [path]` | Proactive briefing from your git diff |
| `coursift onboard <project>` | Generate a codebase tour / onboarding guide |
| `coursift cost` | Token spend attribution per project |
| `coursift health` | Health & tech-debt score per project |
| `coursift serve` | Start MCP server (live agent tools) |
| `coursift sessions` | Browse extracted Claude session decisions |
| `coursift open` | Open the interactive HTML graph |
| `coursift status` | Show graph stats |
| `coursift install` | Install Claude Code skill |
| `coursift uninstall` | Remove Claude Code skill |

---

## Output

```
~/.coursift/
├── graph.json          unified graph (all projects + sessions)
├── graph.html          interactive D3.js visualization
└── GRAPH_REPORT.md     highlights: god nodes, cross-project links, decisions
```

---

## Reading the graph

- **God nodes** ⭐ — the most-connected concepts in your projects
- **Orange nodes/edges** — shared across 2+ projects (shared dependency candidates)
- **Session nodes** 🔵 — Claude conversations with extracted decisions
- **Concept nodes** 🔴 — recurring terms and identifiers from your sessions

---

## Prerequisites

- Python 3.10+
- `ANTHROPIC_API_KEY` in your environment (for `coursift query`)

---

## License

MIT © [Damu-D](https://github.com/Damu-D)
