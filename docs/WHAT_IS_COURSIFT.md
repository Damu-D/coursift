# What is Coursift?

A plain-English guide to what Coursift is, the problems it solves, and how to use it.

---

## 1. In one sentence

> **Coursift gives your AI coding assistant a shared memory and a map of all your projects at once — including everything you and the AI have discussed before — so it stops forgetting, stops inventing code that doesn't exist, and stops repeating past mistakes.**

---

## 2. The simple picture

When you open a project with an AI assistant (Claude Code, Cursor, Copilot, etc.), the AI starts blind every single time. It doesn't know:

- how your code fits together,
- what you decided in past conversations,
- what already failed before,
- or what will break if it changes something.

So it greps around, guesses, and sometimes invents functions or libraries that don't exist.

**Coursift fixes that.** It reads your code *and* your past AI chat logs, builds a connected "map" (a knowledge graph), and lets the AI ask that map precise questions instead of guessing.

Think of it as turning the lights on before the AI walks into the room.

---

## 3. The problems it solves

These are real, documented issues with AI coding tools today:

| Problem | What it means in plain words | Coursift's answer |
|---|---|---|
| **Context rot** | After a while, the AI gets confused and forgets what it already did | `coursift context` gives a small, focused summary instead of dumping everything |
| **Hallucination** | The AI invents functions or packages that don't exist | `coursift verify` checks if something is real before you trust it |
| **No memory** | Close the chat and all knowledge is gone forever | Coursift permanently indexes your past sessions |
| **One project only** | Most tools see one folder; you have many projects | Coursift spans all your registered projects at once |
| **Repeats mistakes** | The AI retries approaches that already failed | `coursift lessons` surfaces what failed before |
| **Blind changes** | The AI edits code without knowing what depends on it | `coursift impact` shows the blast radius first |
| **Leaked secrets** | Passwords/tokens end up in chat logs | Coursift detects and redacts secrets automatically |
| **Unknown cost** | Nobody knows where their AI spend goes | `coursift cost` breaks it down per project |
| **Hard onboarding** | Understanding a new codebase takes weeks | `coursift onboard` writes a "start here" tour |
| **Hidden tech debt** | Quality problems surface months later | `coursift health` scores each project 0–100 |

---

## 4. How it works (3 steps)

```
1. coursift add <folder>     →  tell Coursift which projects to watch
2. coursift build            →  it reads your code + your AI chat logs into a graph
3. coursift <command>        →  ask questions, or let your AI use it automatically
```

When you run `build`, Coursift creates a **knowledge graph** — a web of dots (files, functions, classes, decisions, past failures) connected by lines (who calls whom, who depends on what, what changes together). It saves this locally in `~/.coursift/`.

**Everything runs on your own computer.** No cloud uploads, no account needed. The only time it talks to the internet is if *you* run `coursift query` (which uses your own AI key) — every other command is fully offline.

---

## 5. What you get after a build

```
~/.coursift/
├── graph.json          the full map — every project, function, decision, lesson
├── graph.html          an interactive map you open in your browser
├── GRAPH_REPORT.md     the highlights: key files, surprising links, suggestions
└── CONSTITUTION.md     (optional) rules learned from your past mistakes
```

---

## 6. Everything it can do (commands by group)

### Build the map
| Command | What it does |
|---|---|
| `coursift add <path>` | Register a project to include |
| `coursift remove <path>` | Stop watching a project |
| `coursift list` | Show registered projects |
| `coursift build` | Scan everything into the graph |
| `coursift status` | Show graph stats |
| `coursift open` | Open the interactive browser map |

### Ask questions
| Command | What it does |
|---|---|
| `coursift query "<q>"` | Ask in plain English (uses AI) |
| `coursift context "<q>"` | Get a tight, grounded summary — no AI, saves money |
| `coursift search "<q>"` | Semantic code search across all projects |

### Stop hallucination & mistakes
| Command | What it does |
|---|---|
| `coursift verify <symbol>` | "Does this function/class really exist?" |
| `coursift lessons` | What already failed here before |
| `coursift impact <symbol>` | What breaks if you change this (blast radius) |
| `coursift coupling` | Files that always change together |
| `coursift duplicates` | The same logic written in two places |

### Security
| Command | What it does |
|---|---|
| `coursift audit` | Scan memory for prompt-injection / poisoning |
| `coursift secrets` | Find leaked passwords/tokens (auto-redacted on build) |

### Self-improving memory
| Command | What it does |
|---|---|
| `coursift consolidate` | Turn raw failures into wiser, higher-level rules |
| `coursift constitution` | Auto-write a rulebook learned from your mistakes |
| `coursift forget <age>` | Prune old, stale memory |

### Understand, cost, and grade
| Command | What it does |
|---|---|
| `coursift preflight [path]` | Brief the AI from your current changes, before you code |
| `coursift onboard <project>` | Generate a "start here" tour of a codebase |
| `coursift cost` | Token spend per project |
| `coursift health` | Tech-debt / health score per project |

### Connect to AI tools
| Command | What it does |
|---|---|
| `coursift install --platform all` | Set it up for every AI agent you use |
| `coursift serve` | Run a live MCP server so the AI can call Coursift as tools |

---

## 7. Works with every AI coding agent

Coursift writes its instructions in the format each tool expects, so they all know how to use the graph:

- **Claude Code** — installed as a skill
- **Cursor** — `.cursor/rules/`
- **GitHub Copilot** — `.github/copilot-instructions.md`
- **Gemini CLI** — `GEMINI.md`
- **Windsurf, Cline, Codex, OpenCode, Zed, Aider** — native config
- **20+ others** — via the universal `AGENTS.md` standard

One command sets them all up:

```bash
coursift install --platform all
```

---

## 8. Install it

```bash
# Recommended (puts the `coursift` command on your PATH)
uv tool install coursift
# or
pipx install coursift

# then
coursift add ~/path/to/your/project
coursift build
```

Requirements: Python 3.10+. That's it — no database, no server, no heavy AI libraries.

---

## 9. Why it's built the way it is

- **Local-first.** Your code and conversations never leave your machine. Developers trust local tools.
- **No heavy dependencies.** The semantic search is a hand-written engine in pure Python — no numpy, no PyTorch, no embeddings API. It runs offline anywhere.
- **Grounded, not guessing.** Every answer comes from the real graph, which is why it can catch hallucinations instead of adding to them.
- **Memory that improves.** Old, trivial knowledge is pruned; recurring failures become rules. The graph gets *wiser* over time, not just bigger.

---

## 10. Quick FAQ

**Does it send my code anywhere?**
No. Everything is local except `coursift query`, which uses your own AI key — and only if you choose to run it.

**Do I need an API key?**
Only for `coursift query`. Every other command works fully offline.

**What languages does it understand?**
Python deeply (full parsing). TypeScript/JavaScript and many others at a structural level. Docs, configs, and your chat logs too.

**Will it slow my machine down?**
No. A build takes seconds and runs on demand. Nothing runs in the background unless you start the MCP server.

**Is my data safe?**
Yes — it actively detects and redacts secrets, scans memory for tampering, and never stores raw credentials.

---

*Coursift — give your AI a memory and a map.*
