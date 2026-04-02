---
name: analyze-code
description: |-
  When the user wants to analyze or check code quality.
  When the user wants to lint the codebase.
  When the user asks to check the project for quality issues.
tools:
  - read
  - search
  - exec
---

## Description
Parse and analyze codebase for quality issues.

## Tools
read, search, exec

## Triggers
- analyze code
- check quality
- lint

## Output
Quality report with suggestions

## Usage
```bash
prg analyze .
```
(Note: The original index said `analyze-code src/` but `prg analyze` is the actual command)
