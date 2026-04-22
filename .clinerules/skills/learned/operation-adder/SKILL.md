---
name: operation-adder
description: |
  > **The First AI That Learns Your Coding Style**. Use when user mentions "operation", "adder", "operation adder", "add operation". Do NOT activate for "general operation adder questions", "operation adder theory".
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
  tags: [operation, adder, python]
---

# Skill: Operation Adder

## Purpose
> **The First AI That Learns Your Coding Style**

## Auto-Trigger
- User mentions: "operation", "adder"
- FFmpeg operations needed
- Working in frontend code: *.tsx, *.jsx, *.ts
- Working in backend code: *.py

## Process

### 1. Run

```bash
project-rules-generator .
```

### 2. - Python 3.11 or higher

### 3. - Git

### 4. Run

```bash
git clone https://github.com/Amitro123/project-rules-generator
cd project-rules-generator
pip install -e .
```

### 5. Run

```bash
prg --version
```

## Output

Applying this skill produces:

- Updated or created files following `operation adder` patterns
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
[![Tests](https://img.shields.io/badge/Tests-465%20Passing-green.svg)](tests/)

Most rule generators give you static templates. **Project Rules Generat
