---
name: <% tp.file.title | replace(" ", "-") | lower %>
description: <!-- ONE sentence: what the skill does AND when to trigger. See guide below. [REQUIRED] -->
created: <% tp.date.now("YYYY-MM-DD") %>
status: draft
type: skill
project: <% tp.file.folder() %>
license: MIT
allowed-tools:
  # [REQUIRED] List only the tools the skill actually needs. Avoid `*` — it
  # disables the principle of least privilege. Common values:
  #   Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
  - Read
  - Write
  - Edit
metadata:
  author: <% tp.user.name | default("PRG") %>
  version: 1.0.0
  category: <!-- e.g. "code-generation", "analysis", "io". [REQUIRED] -->
  tags: []
triggers:
  # [REQUIRED] Phrases the user might say that should activate this skill.
  # 3-7 entries. Mix formal and casual phrasings. Each on its own line.
  - <!-- e.g. "create a SPEC for X" -->
  - <!-- e.g. "draft a feature spec" -->
---

# Skill: <% tp.file.title %>

<!--
TEMPLATE: SKILL.md (strict variant)
PURPOSE: A reusable agent skill — used by Claude/Cowork/PRG to perform a
specific task with predictable output.
WHEN TO USE: When you have a workflow that recurs and you want both humans
and AI agents to execute it the same way every time.

VALIDATION RULES (PRG enforces all of these):
  V1. Frontmatter must include: name, description, type=skill, allowed-tools, triggers.
  V2. `description` must be a single line, 80-280 chars, contain a verb-led
      action AND at least one trigger phrase ("when the user...", "use whenever...").
  V3. `triggers` must contain 3-7 entries, no duplicates.
  V4. `allowed-tools` must be a non-empty list. `*` is rejected.
  V5. Every body section header below marked [REQUIRED] must be present and
      non-empty after filling.
  V6. `Process` must contain numbered steps (regex: `^### \d+\. `).
  V7. `Output` must specify a deterministic shape (file structure, JSON schema,
      or fenced template). "Plain prose" output is rejected.
  V8. `Anti-Patterns` must contain at least 2 entries.
  V9. No `<!-- GUIDE -->` HTML comments may remain after the skill is filled.

When PRG validates a SKILL.md and any rule fails, it prints the rule ID and
the offending location.
-->

## Description Guide

<!--
This is documentation for the description field in frontmatter. Move the final
description into frontmatter and delete this section before saving.

GUIDE: One sentence (80-280 chars). Two halves separated by a period:
  Half 1: What the skill does, in active voice.
  Half 2: When to trigger it, including 1-2 example phrasings.

RULES:
  - "use whenever the user asks to..." or "trigger when..." somewhere in the second half.
  - Mention specific user phrases the skill should respond to.
  - Don't be cute. Be operational.

GOOD EXAMPLE:
  "Generate a SPEC.md from a free-form feature description, filling every
  required section with project-specific content. Use whenever the user asks
  to 'spec out', 'draft a spec for', or 'write a SPEC for' a feature."

BAD EXAMPLES:
  "A skill for specs."  (too short, no triggers)
  "Helps with specs by doing things related to specs."  (vague, circular)
-->

## Purpose [REQUIRED]

<!--
GUIDE: 1-2 paragraphs. What this skill exists to do, and what value it
provides over the agent doing it ad-hoc.
RULES:
  - State the deterministic guarantee: "Every output will have shape X."
  - Mention the upstream/downstream context (what other skills feed in or out).
EXAMPLE:
  Generate a fully-populated SPEC.md from a free-form description of a feature.
  This skill exists because spec quality varies wildly when the agent improvises —
  with this skill, every generated spec has the same seven sections, the same
  validation markers, and the same level of detail.

  Output is consumed by `prg analyze --ai` for downstream task generation, and
  by humans reviewing in Obsidian.
STATUS: [REQUIRED]
-->

## Auto-Trigger [REQUIRED]

<!--
GUIDE: List the user phrases that should activate this skill, plus any project
context signals that make activation more confident.
RULES:
  - Mirror the `triggers` list in frontmatter, but with more detail per entry.
  - Add "Do not trigger when..." with negative cases (lookalikes that should NOT activate this skill).
FORMAT:
  ### Triggers
  - "phrase 1" — context: ...
  - "phrase 2" — context: ...

  ### Do not trigger when
  - User asks for "X" — that's [other skill].
EXAMPLE:
  ### Triggers
  - "spec out the [feature]" — user is starting a new feature.
  - "draft a SPEC.md for X" — explicit request for the artifact.
  - "I need a spec for the [thing]" — user has a vague idea, wants structure.

  ### Do not trigger when
  - User asks to update an EXISTING spec — use `update-spec` skill.
  - User wants a one-line description — answer in chat, no skill needed.
  - User asks for a PLAN.md — that's a different artifact; use `generate-plan` skill.
STATUS: [REQUIRED]
-->

## Process [REQUIRED]

<!--
GUIDE: Numbered steps (### 1., ### 2., ...) the agent follows. Each step
should produce a concrete, observable side-effect or decision.
RULES:
  - 3-8 steps total.
  - Heading format MUST be "### 1. Step name" — PRG validation regex depends on it.
  - Each step body: 1-4 sentences explaining what to do AND how to know it succeeded.
EXAMPLE:
  ### 1. Gather inputs
  Read the user's description, any linked SPECs, and the project's CLAUDE.md
  for context. If the description is shorter than 2 sentences, ask one
  clarifying question before proceeding. Success: you can summarize the feature
  in 3 sentences without guessing.

  ### 2. Apply the SPEC.md template
  Open templates/SPEC.md, fill each section using the description and project
  context. Replace every `<!-- GUIDE -->` comment with concrete content; do not
  leave placeholders.

  ### 3. Validate
  Re-read each section against the rules in its (now-deleted) GUIDE comment.
  Confirm: no `<!-- GUIDE -->` comments remain, every [REQUIRED] section is
  non-empty, Acceptance Criteria has >=1 checkbox.

  ### 4. Save and report
  Write to `specs/<feature-slug>-SPEC.md`. Print the path and a one-paragraph
  summary of what the spec covers.
STATUS: [REQUIRED] — must contain at least 3 numbered steps.
-->

## Output [REQUIRED]

<!--
GUIDE: Specify the EXACT shape of what this skill produces. Determinism is
the whole point — vague output specs defeat the purpose.
RULES:
  - File output: state the path, filename pattern, and template the output follows.
  - Structured data output: include a JSON schema or annotated example.
  - Stdout-only: include a fenced exact-format example.
  - "Plain prose" is rejected by PRG validation.
EXAMPLE:
  ### File output
  Path: `specs/<feature-slug>-SPEC.md`
  Template: `templates/SPEC.md` (full variant)
  Filename: kebab-case slug derived from the feature title.

  ### Stdout
  ```
  Wrote: specs/security-monitor-SPEC.md
  Sections filled: 6/7 (Open Questions empty)
  Validation: PASS
  ```
STATUS: [REQUIRED]
-->

## Anti-Patterns [REQUIRED]

<!--
GUIDE: At least 2 things this skill should NOT do, paired with what it should
do instead. These are caught from real failure modes, not hypotheticals.
RULES:
  - Format: ❌ Don't [bad behavior] / ✅ Do [good behavior]
  - Include at least 2; aim for 4-6.
EXAMPLE:
  ❌ Don't fill Acceptance Criteria with vague items like "works correctly".
  ✅ Do reference concrete values, files, or behaviors that can be tested.

  ❌ Don't leave the Open Questions section as a graveyard of resolved questions.
  ✅ Do move resolved answers into the relevant section and delete the question.

  ❌ Don't infer goals the user didn't state.
  ✅ Do ask one focused clarifying question if the description is too thin.

  ❌ Don't generate a Plan inside the SPEC. SPEC describes WHAT, PLAN describes HOW.
  ✅ Do leave phase/timeline questions for PLAN.md.
STATUS: [REQUIRED] — must contain at least 2 ❌/✅ pairs.
-->
