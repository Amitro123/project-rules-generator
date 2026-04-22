---
name: cli-testing
description: |
  Most rule generators give you static templates. Project Rules Generator (PRG) reads your code, understands your architecture, and learns from your patterns to create smarter, context-aware `.clinerules` for any AI agent (Claude, Cursor, Windsurf, Gemini). Use when user mentions "cli", "testing", "cli testing", "add cli". Do NOT activate for "general cli testing questions", "cli testing theory".
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  author: PRG
  version: 1.0.0
  category: project
  tags: [cli, testing, python]
---

# Skill: Cli Testing

## Purpose
Most rule generators give you static templates. Project Rules Generator (PRG) reads your code, understands your architecture, and learns from your patterns to create smarter, context-aware `.clinerules` for any AI agent (Claude, Cursor, Windsurf, Gemini)

## Auto-Trigger
- User mentions: "cli", "testing"

## Process

### 1. Run

```bash
prg analyze . --no-commit
```

### 2. Run

```bash
export ANTHROPIC_API_KEY=sk-ant-...
prg analyze . --ai
```

## Output

Applying this skill produces:

- Updated or created files following `cli testing` patterns
- Status report with changes made
- Recommendations for next steps

## Anti-Patterns
❌ Missing FFmpeg availability check in test_ai_video_detection.py ג†’ Add: `if not shutil.which('ffmpeg'): raise RuntimeError('ffmpeg not found')`

## Tech Stack
python, react, gemini, claude, ffmpeg

## Context (from README) *(truncated — see README.md for full content)*

# Project Rules Generator 🚀

> **The First AI That Learns Your Coding Style**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-512%20Passing-green.svg)](tests/)

Most rule generators give you static templates. **Project Rules Generat
