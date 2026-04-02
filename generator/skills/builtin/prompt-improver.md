---
name: prompt-improver
description: |-
  When the user wants to improve a system prompt or agent instructions.
  When the agent is failing to follow instructions consistently.
  When the user wants to fix hallucinations or inconsistent output.
tools:
  - read
  - exec
---

# Skill: Prompt Improver

## Purpose
Without structured prompt improvement, developers often patch prompts symptomatically — adding more instructions that contradict existing ones, making the problem worse. This skill diagnoses and fixes the root cause of prompt failures systematically.

## Auto-Trigger
- Agent is failing to follow instructions consistently
- User sees hallucinations or unexpected formatting
- User says: "improve this prompt", "fix the agent instructions"

## Process

### 1. Diagnose the Failure
Identify the exact failure mode before changing anything — vague fixes introduce new problems.
- What is the agent doing wrong?
- Is it a missing instruction, an ambiguous instruction, or a contradicting instruction?
- Does the failure reproduce consistently or only sometimes?

### 2. Locate the Root Cause
```bash
# Review the current prompt
cat .clinerules/agents/agent-name.md
```
Look for: missing constraints, conflicting rules, ambiguous phrasing, and missing examples.

### 3. Apply Targeted Fix
Fix one issue at a time and test after each change — stacking multiple changes makes it impossible to know which one helped.
- Add a clear constraint if behavior is undefined
- Add an example if the instruction is ambiguous
- Remove or consolidate contradicting rules

### 4. Test the Improvement
Re-run the scenario that originally failed to verify the fix works before moving on.

## Output
Improved prompt with:
- Change summary (what was wrong and why it was fixed)
- Before/after comparison of the changed section

## Anti-Patterns
❌ Adding more instructions without removing the conflicting ones
❌ Changing multiple things at once (can't isolate what helped)
❌ Not testing with the original failure scenario
❌ Vague instructions like "be careful" without defining what careful means
