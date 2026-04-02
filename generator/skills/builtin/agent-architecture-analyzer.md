---
name: agent-architecture-analyzer
description: |-
  When the user wants to analyze or review the agent architecture.
  When the user wants to check or improve multi-agent workflows.
  When the user is debugging agent loops or planning new agent capabilities.
tools:
  - read
  - search
---

# Skill: Agent Architecture Analyzer

## Purpose
Without a structured review, agent architectures accumulate silent failures — missing tool permissions, broken handoffs, and circular dependencies that only surface under load. This skill systematically maps agent roles, identifies coordination gaps, and surfaces improvements before they become incidents.

## Auto-Trigger
- User says: "analyze agent", "check architecture", "review my agents"
- Debugging agent loops or coordination failures
- Planning new agent capabilities or adding a new agent role

## Process

### 1. Map the Architecture
Read all agent definitions to understand roles, tools, triggers, and communication patterns — you cannot improve what you have not fully understood.
```bash
find .clinerules/agents ~/.claude/agents -name "*.md" 2>/dev/null | xargs grep -l "name:"
```

### 2. Identify Bottlenecks and Gaps
Look for single points of failure, missing tool grants, and agents that need capabilities they lack.
- Which agents share state or pass outputs to each other?
- Are there circular dependencies?
- Does any agent lack a tool it needs?

### 3. Review Tool Coverage
Verify each agent has exactly the tools it needs — over-permissioned agents increase blast radius, under-permissioned agents fail silently.

### 4. Suggest Improvements
Provide concrete, ranked recommendations with rationale for each issue found.

## Output
Architecture review with:
- Agent role map (who does what, who calls whom)
- Identified issues with severity (HIGH / MEDIUM / LOW)
- Recommended changes with justification

## Anti-Patterns
❌ Analyzing agents in isolation without tracing the full task flow
❌ Recommending changes without understanding existing handoffs
❌ Missing edge cases in agent coordination (e.g. timeout handling)
