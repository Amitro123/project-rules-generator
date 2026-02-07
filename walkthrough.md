# Skills System Walkthrough

This guide walks you through the new Skills System in Project Rules Generator.

## Overview
The Skills System allows you to manage a library of skills that can be used by AI agents. Skills are organized into three categories:
- **Built-in**: Core skills provided by the tool.
- **Awesome**: Curated skills from the community.
- **Learned**: Custom skills created for your projects.

## Commands

### Listing Skills
To see all available skills:
```bash
python main.py --list-skills
```
Output:
```
Available Skills (7 found):

📁 Builtin:
  - brainstorming
  - meta/writing-skills
  - requesting-code-review
  - subagent-driven-development
  - systematic-debugging
  - test-driven-development
  - writing-plans
```

### Creating a Skill
To create a new skill in your learned library:
```bash
python main.py --create-skill my-new-skill
```
This creates `skills/learned/my-new-skill/SKILL.md` with a template.

### Creating from README
To create a skill based on an existing README (e.g., converting a project's documentation into a skill):
```bash
python main.py --create-skill video-processing --from-readme ./docs/video-workflow.md
```
This includes the content of the README in the `SKILL.md` file as context.

## Skill Structure
Each skill is a directory containing a `SKILL.md` file. The format is:

```markdown
# Skill Name

## Purpose
What does this skill do?

## Auto-Trigger
When should the agent use this skill?

## Process
1. Step 1
2. Step 2

## Anti-Patterns
What to avoid?
```

## Next Steps
- Try creating a skill for your current workflow.
- Explore the built-in skills to see examples.
