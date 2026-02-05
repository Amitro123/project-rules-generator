# Project Documentation Generator - Agent Prompt

Use this prompt in IDE agents (Claude, Gemini, Cursor) to enable automatic rules/skills generation.

## Trigger Phrases

When user says any of these, run the generator:
- "generate docs"
- "create rules"
- "generate project rules"
- "create documentation for this project"
- "analyze README and make rules"
- "make rules and skills for this project"

## Required Actions

### 1. Detect Project Path
```python
import os
current_workspace = os.getcwd()  # Or use IDE's workspace detection
```

### 2. Run Generator
```bash
# Adjust path to where project-rules-generator is installed
python /path/to/project-rules-generator/main.py {workspace_path} --verbose
```

### 3. Parse Output
- Extract generated file paths from output
- Read first 20 lines of each file
- Show summary to user

### 4. Ask for Git Commit
```
"Generated files:
- {project}-rules.md
- {project}-skills.md

Commit to git? (yes/no)"
```

### 5. If Yes: Commit
```bash
python /path/to/project-rules-generator/main.py {workspace_path} --commit
```

## Response Format

Always respond with:
1. What was detected (project name, tech stack)
2. What files were created
3. Quick preview of each file (YAML frontmatter + first section)
4. Suggestion to review and customize the files

## Example Full Response

```
Generated rules and skills for {project-name}

Tech stack detected: python, fastapi, docker

Files created:
- {project-name}-rules.md (coding standards)
- {project-name}-skills.md (agent capabilities)

Preview:
---
project: {project-name}
purpose: Coding & contribution rules
---

## DO
- Use python, fastapi, docker as primary stack
...

Next steps:
1. Review generated files
2. Customize based on team preferences
3. Commit to git when ready
```

## Testing Requirements

Test this agent prompt on:
1. This project itself (project-rules-generator)
2. One real project (e.g., mcp-python-auditor or MediaLens-AI)
3. Verify output is accurate and complete
