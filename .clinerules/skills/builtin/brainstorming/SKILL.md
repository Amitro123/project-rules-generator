---
name: brainstorming
description: |-
  When the user wants to add a new feature or capability.
  When the user says "I want to build" or "I'm thinking about".
  When requirements are unclear and need to be refined.
tools:
  - read
---

# Skill: Brainstorming & Design Refinement

## Purpose
Without a structured design phase, developers often skip straight to implementation — producing code that solves the wrong problem or misses critical edge cases. This skill prevents that by refining vague ideas into concrete, implementable designs through Socratic questioning before any code is written.

## Auto-Trigger
- User says: "I want to add...", "Let's build...", "I'm thinking about..."
- Before any code is written
- When requirements are unclear

## Process

### Stage 1: Clarify the Goal
Ask:
1. What problem are you trying to solve?
2. Who is the user/consumer of this feature?
3. What does success look like?

### Stage 2: Explore Alternatives
Present 2-3 approaches with trade-offs:
- Simplest solution
- Most robust solution
- Hybrid approach

### Stage 3: Define Scope
Break down into:
- Must have (MVP)
- Nice to have
- Out of scope (for now)

### Stage 4: Present Design
Show design in digestible chunks (max 10 lines per section):
- Data models
- API contracts
- Key algorithms
- Edge cases

### Stage 5: Get Sign-Off
Wait for explicit approval before proceeding.

## Output
Create `DESIGN.md` with:
- Problem statement
- Chosen approach
- Implementation outline
- Success criteria

```bash
# Verify DESIGN.md was created after the session
cat DESIGN.md
```

## Anti-Patterns
❌ Jumping to implementation without design
❌ Overwhelming user with too much info at once
❌ Not exploring alternatives
❌ Missing edge cases
