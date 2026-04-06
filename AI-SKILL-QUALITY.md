# AI Skill Generation Quality Analysis

## Summary
The quality of AI-generated skills varies significantly. Some skills are rich and project-specific, while others are template-heavy with placeholders.

## Observation Table

| Skill Name | Quality | Detail Level | Note |
|---|---|---|---|
| `claude-cowork-workflow` | Excellent | High | Deeply integrated, specific bash commands, 5.6KB. |
| `fastapi-endpoints` | Poor | Low (Template) | Mostly placeholders (`[First step]`, `[description]`). |
| `gitpython-ops` | Poor | Low (Template) | Mostly placeholders. |
| `docker-deployment` | Poor | Low (Template) | Mostly placeholders. |

## Technical Findings
1. **Dependency Mismatch**: `fastapi` is NOT a dependency of this project. The AI generated a skill for it based on documentation mentions, but found no code to ground it, resulting in a template.
2. **Context Extraction**: For `gitpython-ops`, the dependency exists, but the AI still produced a template. This suggests the project scanner might have missed the files where `GitPython` (imported as `git`) is used, or the `Relevant Files` mapping for `ops` or `gitpython` is too narrow.
3. **Template Fallback**: The presence of `[First step]` and `[description]` confirms the system is using a fallback when the AI fails to generate specific content or when the context provided is negligible.

## Quality of Multi-Step Skills
- `claude-cowork-workflow.md` is the gold standard here. It was likely generated with full project context because `anthropic` is a key part of the project.


## Recommendations
- Improve pre-generation reconnaissance to find more relevant files for each detected technology.
- Increase the strictness of the quality gate before accepting a skill.
- Use better prompts that discourage placeholders.
