<div align="center">
  <h1>Coursift</h1>
  <p><strong>A cross-project knowledge graph and memory layer for AI coding agents.</strong></p>
  <p>Maps your code, AI conversations, and decisions across <em>all</em> your projects — not just one.</p>
  <p>📖 New here? Read <a href="docs/WHAT_IS_COURSIFT.md"><strong>What is Coursift?</strong></a> for a plain-English overview.</p>

  <a href="https://pypi.org/project/coursift/"><img src="https://img.shields.io/pypi/v/coursift?color=7c3aed" alt="PyPI"/></a>
  <a href="https://github.com/Damu-D/coursift/actions"><img src="https://github.com/Damu-D/coursift/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <img src="https://img.shields.io/pypi/pyversions/coursift" alt="Python versions"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
</div>

---

## What is Coursift?

AI coding assistants understand one project at a time and forget everything when a session ends. Coursift builds a single, queryable knowledge graph from **all** your projects — your code plus your past AI sessions — so your assistant can look things up instead of guessing.

It runs entirely on your machine. No account, no cloud, no uploads.

```bash
coursift add ~/projects/myapp
coursift add ~/projects/api-service
coursift build
coursift query "which projects share the same auth pattern?"
```

---

## Features

- **Unified graph** across all your registered projects
- **Session memory** — decisions and context extracted from your past AI sessions
- **Grounded context** — `context` returns a small, relevant slice of the graph instead of whole files
- **Anti-hallucination** — `verify` confirms a symbol actually exists
- **Impact analysis** — `impact` shows what depends on a symbol before you change it
- **Failure memory** — `lessons` surfaces what already failed, so it isn't repeated
- **Semantic search** — find code by meaning, fully offline
- **Duplicate detection** — spot the same logic written in two places
- **Security** — scans memory for prompt-injection and redacts leaked secrets
- **Health & cost** — a 0–100 tech-debt score and token-spend breakdown per project
- **Interactive graph** — open it in your browser

Everything is pure Python. No numpy, no PyTorch, no embeddings server.

---

## Install

```bash
# Recommended (puts `coursift` on your PATH)
uv tool install coursift

# Or
pipx install coursift
pip install coursift
```

Requires Python 3.10+.

---

## Quickstart

```bash
coursift add ~/projects/myapp        # register one or more projects
coursift build                       # build the graph
coursift open                        # explore it in your browser
```

Set it up for your AI agent:

```bash
coursift install --platform all      # configure every supported agent
coursift install --platform cursor   # or just one
```

---

## Works with every AI coding agent

Coursift writes its instructions in the format each tool expects:

**Claude Code, Cursor, GitHub Copilot, Gemini CLI, Windsurf, Cline, Codex, OpenCode, Zed, Aider** — plus the universal **`AGENTS.md`** standard that many other agents read natively.

---

## Commands

| Command | What it does |
|---|---|
| `coursift add <path>` | Register a project |
| `coursift remove <path>` | Unregister a project |
| `coursift list` | List registered projects |
| `coursift build` | Build the graph |
| `coursift status` | Show graph stats |
| `coursift open` | Open the interactive graph |
| `coursift query "<q>"` | Ask a question (uses your AI key) |
| `coursift context "<q>"` | Token-budgeted grounded context (local) |
| `coursift search "<q>"` | Semantic code search (local) |
| `coursift verify <symbol>` | Check whether a symbol exists |
| `coursift impact <symbol>` | What depends on this (blast radius) |
| `coursift lessons` | Past failures from your sessions |
| `coursift coupling` | Files that change together (git) |
| `coursift duplicates` | Cross-project duplicate logic |
| `coursift deps` | Dependency audit |
| `coursift drift` | Documentation drift detector |
| `coursift audit` | Memory injection scan |
| `coursift secrets` | Scan memory for leaked credentials |
| `coursift forget <age>` | Prune stale memory |
| `coursift consolidate` | Distill failures into insights |
| `coursift constitution` | Generate a project rules file |
| `coursift preflight [path]` | Briefing from your current git diff |
| `coursift onboard <project>` | Generate a codebase tour |
| `coursift cost` | Token spend per project |
| `coursift health` | Health / tech-debt score per project |
| `coursift sessions` | Browse extracted session decisions |
| `coursift install [--platform <p>]` | Set up for an AI agent |
| `coursift serve` | Start the MCP server |

---

## Output

```
~/.coursift/
├── graph.json          the graph (all projects + sessions)
├── graph.html          interactive visualization
└── GRAPH_REPORT.md     highlights and key files
```

---

## Project scoping

The graph holds all your projects, but commands focus on **the project you're working in** so results stay clean. When you run a command from inside a registered project's folder, Coursift auto-scopes to it:

```bash
cd ~/projects/myapp
coursift verify config       # only myapp's `config`, not every project's
coursift search "auth"       # only myapp results
```

Override when you want to:

```bash
coursift verify config --all            # search every project
coursift search "auth" --project other  # a specific project
```

Commands that scope: `search`, `verify`, `context`, `impact`, `lessons`. God-node rankings and health are computed per project, so a large project never drowns out a small one.

---

## How it works

`build` scans each registered project (Python via AST; other languages structurally) and reads your local AI session logs, then connects everything into one graph saved under `~/.coursift/`. Commands auto-scope to the project you're in (override with `--all` / `--project`). Every command except `query` runs fully offline; `query` uses your own `ANTHROPIC_API_KEY`.

---

## License

MIT © [Damu-D](https://github.com/Damu-D)
