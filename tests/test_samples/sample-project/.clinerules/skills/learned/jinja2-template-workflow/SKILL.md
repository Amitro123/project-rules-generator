---
name: jinja2-template-workflow
description: |
  > Build dynamic code and configuration files from structured templates. Use when user mentions "jinja2", "template", "jinja2 template workflow", "add jinja2". Do NOT activate for "general jinja2 template workflow questions", "jinja2 template workflow theory".
license: MIT
allowed-tools: "Bash Read Write Edit Glob Grep"
metadata:
  author: PRG
  version: 1.0.0
  category: project
  tags: [jinja2, template, workflow, python]
---

# Skill: Jinja2 Template Workflow

## Purpose
> Build dynamic code and configuration files from structured templates

## Auto-Trigger
- User mentions: "jinja2", "template", "workflow"
- Working in backend code: *.py
- Working with *.j2 files

## Process

### 1. Clone the repository:

### 2. Run

   ```bash
   git clone https://github.com/example/jinja2-codegen.git
   cd jinja2-codegen
   ```

### 3. Install dependencies:

### 4. Run

   ```bash
   pip install -e .
   ```

### 5. Verify:

### 6. Run

   ```bash
   python -m jinja2_codegen --version
   ```

### 7. Create a template file (`templates/model.py.j2`):

### 8. Run

   ```jinja2
   class {{ class_name }}(BaseModel):
       {% for field in fields %}
       {{ field.name }}: {{ field.type }}
       {% endfor %}
   ```

### 9. Render from CLI:

### 10. Run

   ```bash
   codegen render templates/model.py.j2 --var class_name=User --var fields='[...]'
   ```

## Output

Applying this skill produces:

- Updated or created files following `jinja2 template workflow` patterns
- Status report with changes made
- Recommendations for next steps

## Anti-Patterns
❌ Never use `Undefined` (default) — always use `StrictUndefined` so missing
❌ Don't put business logic in templates — keep templates declarative.
❌ Don't use `render_template_string` on untrusted input — always load from

## Tech Stack
python, click, pydantic

## Context (from README) *(truncated — see README.md for full content)*


# Jinja2 Template Engine — Code Generator

> Build dynamic code and configuration files from structured templates.

A Python tool that uses **Jinja2** to render typed templates into source code,
configuration files, and documentation. Works with Click for CLI and Pydantic
for schema validation.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/example/jinja2-co
