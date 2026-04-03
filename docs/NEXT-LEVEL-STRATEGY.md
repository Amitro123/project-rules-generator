# How to Take PRG to the Next Level

You've got a solid, working tool with a good architecture. Here's where I'd focus energy, broken into tiers by impact.

## Tier 1 — High Impact, Relatively Achievable

### 1. Skills that learn from actual usage
This is the biggest gap called out in your own roadmap ("Evolution System — NOT IMPLEMENTED"). Right now skills are static — they're generated once and never improve.
**The missing loop:**
*   When a user runs `prg agent "fix a bug"` and the matched skill is used → track it.
*   When a user edits a generated skill → treat the delta as a signal.
*   Surface: `prg skills feedback <skill> --useful/--not-useful`.
*   Store a simple score in the skill's frontmatter. Skills that score low get flagged for regeneration on next `prg analyze --incremental`.

This turns PRG from a one-shot generator into something that actually gets smarter with the project over time — which is the core product promise.

### 2. `prg watch` — live mode
Right now everything is on-demand. A watch mode would run `prg analyze --incremental` automatically when files change (`README`, `pyproject.toml`, new test files, etc.).
Implementation is straightforward with `watchdog`.
**The value:** rules stay current with zero effort. This is a strong UX story for teams.

### 3. VS Code / IDE extension
The tool is CLI-only right now. A VS Code extension that:
*   Shows a "PRG" status bar item with current rule count.
*   Triggers `prg agent` on right-click in the editor ("Find skill for this...").
*   Highlights when `.clinerules/rules.md` is out of date.

This dramatically expands the audience. Most developers discover tools through their editor, not through `pip install`.

### 4. PyPI publishing
Right now installation requires `git clone + pip install -e .`. Publishing to PyPI means `pip install project-rules-generator` — that's the difference between a personal tool and something people actually share.
The `pyproject.toml` is already well-structured for this. You'd need to sort out: a real author email, a real version bump to 0.3.0, and a publish CI step.

## Tier 2 — Medium Impact, More Work

### 5. GitHub Actions integration
A `prg-action` that runs on PRs and posts a comment: "Your `rules.md` may be outdated — detected changes in `pyproject.toml` and `requirements.txt`." This makes PRG part of the team's CI loop rather than something one person runs occasionally.

### 6. Multi-file project context (beyond README)
Right now PRG's primary intelligence source is the README. Good projects often have `CONTRIBUTING.md`, `ADRs/`, `docs/architecture.md`, `openapi.yaml`, migration files. Ingesting these would produce dramatically richer rules — especially the "don't do X" patterns that tend to live in architecture docs, not READMEs.

### 7. LiteLLM as the provider layer
You currently maintain four separate AI client implementations (`groq_client.py`, `anthropic_client.py`, etc.) — that's a real maintenance burden.
**LiteLLM** is a unified interface that handles all of them plus 100+ more providers. Replacing your `ai/` layer with LiteLLM would:
*   Shrink the codebase.
*   Give you instant access to new models.
*   Eliminate the provider-specific bugs you've been fixing in CR #1–3.

### 8. MCP server
Model Context Protocol is becoming the standard way AI agents consume tools. Exposing PRG as an MCP server means Claude, Cursor, Windsurf etc. can call `prg analyze` and `prg agent` directly from within their agent loops — without the user running anything manually. This is the most direct path to making PRG invisible (which is the goal — rules should just be there).

## Tier 3 — Architectural Cleanup (already on your roadmap)

### 9. Replace `except Exception` with specific types
95 broad catches across the codebase. These swallow real bugs silently. `analyze_cmd.py` already has comments like "Context extraction skipped: {exc}" — those are cases where a specific `FileNotFoundError` or `yaml.YAMLError` would be far more debuggable.

### 10. `analyze_cmd.py` god object
Still 411 lines. Your roadmap has "H4: extract AnalyzePipeline" — this is worth doing before adding more features to that file, because right now adding anything to the analyze flow means touching a 400-line file.

---

## The One Thing I'd Do First
If I had to pick one: **PyPI publishing + `prg watch`**, in that order.

*   **Publishing** unlocks distribution — people can try PRG without reading a GitHub README first.
*   **`prg watch`** demonstrates the core value proposition in a way that's immediately tangible: "I pushed a change to my requirements.txt and my rules updated automatically." That's the demo moment that makes people want to share the tool.

The **MCP server** idea is the highest ceiling long-term — if agents can pull PRG context automatically, the tool becomes infrastructure rather than a CLI you remember to run.
