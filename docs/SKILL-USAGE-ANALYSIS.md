# Feature 14 Analysis: Skill Usage Tracking

This document summarizes the findings from checking **Skill Usage Tracking**.

## Status: Functional & Integrated

The feature is well-implemented and currently lives in:
- Core: `generator/skill_tracker.py`
- CLI: `cli/skills_cmd.py` (`feedback`, `stale` commands)
- Integration: `generator/planning/agent_executor.py`

### Key Strengths
1. **Global Persistence**: Usage data is correctly stored in `~/.project-rules-generator/skill-usage.json`, ensuring results are shared across all of your projects.
2. **"Stale" Logic**: The `stale` command uses a reasonable threshold (default 30%) and a participation requirement (at least 3 votes), preventing premature flagging of new skills.
3. **Automatic Matching**: The `prg agent` command correctly increments `match_count` silently in the background, even when you aren't giving feedback.

## Identified Gaps & Opportunities

### 1. `prg skills list` lacks visibility
Currently, `prg skills list` only shows name, layer, triggers, and tools.
- **Problem**: You have to run `prg skills feedback <name>` just to see how a skill is performing.
- **Enhancement**: Add `Score` and `Matches` columns to the `skills list` table.

### 2. No automatic tracking in `prg start`
The full `start` workflow currently bypasses the skill matching logic.
- **Problem**: If you use a custom skill through a full `prg start` run, your usage isn't tracked.
- **Enhancement**: Integrate `AgentExecutor` into the `AgentWorkflow` setup phase to record a match if the user task aligns with a known skill.

### 3. Feedback Validation
The `feedback` command allows providing feedback on any string.
- **Problem**: Typoing a skill name creates a "zombie" entry in the JSON that will never be matched.
- **Enhancement**: Add a check in the CLI to see if the skill name actually exists in either `builtin` or the current project's `learned` skills.

## Summary

| Component | Status | Note |
| :--- | :--- | :--- |
| **Logic** | ✓ Good | Thread-safe, JSON-backed. |
| **CLI (feedback/stale)** | ✓ Good | Consistent with documentation. |
| **Integration (agent)** | ✓ Good | Silently records matches. |
| **UX (list)** | ⚠ Poor | stats are hidden from the primary list command. |
