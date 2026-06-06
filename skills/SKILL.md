# Coursift — Cross-Project Knowledge Graph & Memory Layer

Coursift maps your code, Claude conversations, and architectural decisions across all your projects into a unified, queryable knowledge graph.

## What makes Coursift different from Graphify

| | Graphify | Coursift |
|---|---|---|
| Scope | One project at a time | All registered projects |
| Claude session history | No | Yes — indexes decisions & context |
| Cross-project links | No | Yes — shared deps shown in orange |
| Why code was written | No | Yes — from conversation history |
| Skill scope | Per-project | Global (every session) |

## When to use the graph

Use `coursift query` instead of grepping files when:
- Looking for a function/pattern across multiple projects
- Asking "why was X implemented this way?"
- Finding cross-project shared dependencies
- Reviewing past architectural decisions

## Quick commands

```bash
coursift add ~/projects/myapp    # register a project
coursift build                   # build unified graph
coursift query "how is auth handled across projects?"
coursift sessions                # browse Claude session decisions
coursift open                    # open interactive browser graph
coursift status                  # graph stats
```

## Graph output

```
~/.coursift/
├── graph.json          queryable graph (all projects + sessions)
├── graph.html          interactive D3.js visualization
└── GRAPH_REPORT.md     highlights, god nodes, cross-project links
```

## Reading the graph

- **God nodes** ⭐ — most connected concepts (everything flows through these)
- **Orange nodes/edges** — shared across 2+ projects (cross-project links)
- **Session nodes** 🔵 — Claude conversations with extracted decisions
- **Concept nodes** 🔴 — recurring terms from your sessions
