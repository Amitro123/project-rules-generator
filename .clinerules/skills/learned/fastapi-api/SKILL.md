---
name: fastapi-api
description: |
  When the user mentions "fastapi api", "fastapi", "api".
  When the user needs help with fastapi api.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
triggers:
  - "fastapi api"
  - "fastapi"
  - "api"
metadata:
  tags: [fastapi, api]
---

# Skill: Fastapi Api

## Purpose

Inconsistent api patterns slow down Fastapi development. Apply this skill to enforce the correct api approach every time.

## Auto-Trigger

Activate when user requests:
- **"fastapi api"**
- **"fastapi"**
- **"api"**

Do NOT activate for: general fastapi questions unrelated to api.

## Process

### 1. Analyze the existing Fastapi setup

```bash
# Review fastapi configuration
grep -r 'fastapi' . --include='*.py' -l
```

### 2. Apply api correctly

Follow established Fastapi conventions for api in this project.

### 3. Validate

Verify the output is correct and tests still pass.

## Output

Updated Fastapi implementation with consistent api patterns applied.

## Anti-Patterns

❌ Use generic Fastapi patterns without checking what this project already does
✅ Read existing Fastapi code first, then apply the same api conventions
