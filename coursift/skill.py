"""
Skill installer — writes SKILL.md to ~/.claude/skills/coursift/ so Claude Code
reads the knowledge graph in every session, across every project.
"""

from pathlib import Path

CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills" / "coursift"
SKILL_CONTENT = """\
# Coursift — Cross-Project Knowledge Graph

You have access to a multi-project knowledge graph built by Coursift.
This graph spans code, Claude conversations, and decisions across all registered projects.

## When to use the graph

Before:
- Searching for a function or file across projects
- Answering "where is X defined?" or "which projects use Y?"
- Explaining architectural decisions
- Finding cross-project patterns or shared dependencies

## Commands

```bash
# Query the graph in natural language
coursift query "what connects auth to the database?"
coursift query "which projects share the same pattern?"
coursift query "why was X implemented this way?"

# See the full interactive graph
open ~/.coursift/graph.html

# Check stats
coursift status
```

## Graph location

The unified graph is at: `~/.coursift/graph.json`
The HTML visualization is at: `~/.coursift/graph.html`

## What makes Coursift different

- Spans ALL registered projects, not just the current one
- Indexes Claude Code session history — knows WHY code was written
- Detects cross-project shared dependencies (shown in orange)
- God nodes (most-connected) are marked with ⭐

When the user asks about patterns, decisions, or cross-project connections,
prefer `coursift query` over grepping files.
"""


def install_skill() -> Path:
    CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    skill_file = CLAUDE_SKILLS_DIR / "SKILL.md"
    skill_file.write_text(SKILL_CONTENT)
    return skill_file


def uninstall_skill() -> bool:
    skill_file = CLAUDE_SKILLS_DIR / "SKILL.md"
    if skill_file.exists():
        skill_file.unlink()
        try:
            CLAUDE_SKILLS_DIR.rmdir()
        except OSError:
            pass
        return True
    return False
