# PLAN

> **Goal:** Robustness and Security Enhancements for Project Analyzer and Autopilot Orchestrator

**Subtasks:** 1
**Estimated time:** 5 minutes

---

## 1. Define `SecurityError` Custom Exception

**Goal:** Create a custom exception class `SecurityError` to signify path validation failures for LLM write operations.
**Depends on:** none
**Estimated:** ~5 min

**Files:**
- `project_analyzer/exceptions.py`

**Changes:**
- Create `project_analyzer/exceptions.py` if it doesn't exist.
- Define `class SecurityError(Exception): pass`.

---
