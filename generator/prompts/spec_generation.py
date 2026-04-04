"""LLM prompt for spec.md generation (used by prg spec --generate with a provider)."""

SPEC_SYSTEM_MESSAGE = "You are a senior product manager. Write precise, actionable project specifications."

SPEC_GENERATION_PROMPT = """\
You are a senior product manager. Based on the project context below, write a complete **spec.md** document.

---
{context_block}
---

Generate a spec.md with EXACTLY these sections (use the headings verbatim):

# Project Specification

## Overview
One paragraph: what this project does, who it's for, and the core problem it solves.

## Goals
3-5 bullet points. Each goal is a concrete, measurable outcome.

## User Personas
2-3 short personas. Format: **Name** (Role) — one sentence describing their need.

## User Stories
5-8 stories in "As a [persona], I want [action] so that [benefit]." format.

## Constraints
Technical and non-functional constraints (performance, security, compatibility, budget, timeline).
Use bullets.

## Acceptance Criteria
Numbered list. Each criterion is testable and unambiguous.
Format: [ID] Given [context], when [action], then [expected result].

## Out of Scope
What this project explicitly does NOT cover. 2-4 bullets.

Rules:
- Be specific to THIS project — no generic filler.
- Do not include section titles not listed above.
- Use clean Markdown only.
"""
