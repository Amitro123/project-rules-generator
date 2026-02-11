# Project Rules Generator - Skills System

## Overview
Skills are modular workflows that guide agents through specific tasks.

## Structure

- **builtin/**: Core skills shipped with the tool
- **awesome/**: Skills cloned from famous open-source projects
- **learned/**: Skills generated from your project's documentation

## Priority
`learned > awesome > builtin`

## Usage

Skills are automatically triggered based on context. You can also:

```bash
# List available skills
python -m project_rules_generator --list-skills

# Create new skill
python -m project_rules_generator --create-skill "my-workflow" --from-readme README.md

# Export skills
python -m project_rules_generator --export-skills-md
```

## Creating Skills
See `builtin/meta/writing-skills/SKILL.md` for guidance.
