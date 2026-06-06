<div align="center">
  <h1>Coursift</h1>
  <p><strong>Cross-project knowledge graph and memory layer for Claude Code.</strong></p>
  <p>Maps your code, Claude conversations, and decisions across <em>all</em> your projects — not just one.</p>

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

## Why not Graphify?

| | [Graphify](https://github.com/safishamsi/graphify) | **Coursift** |
|---|---|---|
| Scope | One folder at a time | All registered projects |
| Claude session history | ✗ | ✓ |
| Cross-project detection | ✗ | ✓ |
| Why code was written | ✗ | ✓ (from your sessions) |
| Skill install | Per-project | Global (every session) |
| PyPI name | `graphifyy` (taken) | `coursift` (clean) |

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
| `coursift query "<question>"` | Ask a question about the graph |
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
