"""Template management for rules and skills generation."""
from pathlib import Path
from typing import Dict, Any
import yaml


def load_template(template_name: str, templates_dir: str = "templates") -> Dict[str, Any]:
    """Load a YAML template file.
    
    Args:
        template_name: Name of template (e.g., 'rules' or 'skills')
        templates_dir: Directory containing templates
        
    Returns:
        Template structure as dict
    """
    template_path = Path(templates_dir) / f"{template_name}_template.yaml"
    
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    # Return default templates if file doesn't exist
    return get_default_template(template_name)


def get_default_template(template_type: str) -> Dict[str, Any]:
    """Get default template structure."""
    
    if template_type == 'rules':
        return {
            'structure': {
                'frontmatter': ['project', 'purpose', 'version'],
                'sections': [
                    'CONTEXT',
                    'DO (must follow)',
                    "DON'T",
                    'PRIORITIES',
                    'WORKFLOWS'
                ]
            },
            'placeholders': {
                'description': '{{description}}',
                'tech_stack': '{{tech_stack}}',
                'features': '{{features}}',
                'project_name': '{{project_name}}'
            }
        }
    
    elif template_type == 'skills':
        return {
            'structure': {
                'frontmatter': ['project', 'purpose'],
                'sections': [
                    'CORE SKILLS',
                    'PROJECT-SPECIFIC SKILLS',
                    'USAGE'
                ]
            },
            'placeholders': {
                'domain': '{{domain}}',
                'project_name': '{{project_name}}'
            }
        }
    
    return {}


# Default inline templates for fallback

RULES_TEMPLATE_MD = """---
project: {project_name}
purpose: Coding & contribution rules for this workspace
version: 1.0
***

## CONTEXT

{description}

This project uses **{tech_stack_str}** as its primary technology stack.

## DO (must follow)

{do_items}

## DON'T

{dont_items}

## PRIORITIES

{priorities}

## WORKFLOWS

{workflows}
"""

SKILLS_TEMPLATE_MD = """---
project: {project_name}
purpose: Agent skills for this project
***

## CORE SKILLS

### analyze-code
Parse {domain} codebase and suggest improvements.

- **Tools**: read, exec
- **Usage**: "analyze-code src/"
- **Output**: Quality report + refactor suggestions

### refactor-module
Refactor code following {project_name}-rules.md guidelines.

- **Input**: Module path
- **Output**: Refactored code + diff

### test-coverage
Run tests and generate coverage report.

- **Tools**: exec, pytest
- **Output**: Coverage % + missing test lines

## PROJECT-SPECIFIC SKILLS

### {domain}-expert
Deep analysis and optimization for {domain} projects.

- **Steps**:
  1. Read project structure
  2. Identify {domain} patterns and conventions
  3. Suggest architecture improvements
  
- **Usage**: "Call the {domain}-expert to review this component"

{custom_skills}

## USAGE

Load these skills in your IDE agent or via:

```
/skills load {project_name}-skills.md
```

Or reference directly when starting a session with the agent.
"""


def get_rules_template() -> str:
    """Get the markdown template for rules generation."""
    return RULES_TEMPLATE_MD


def get_skills_template() -> str:
    """Get the markdown template for skills generation."""
    return SKILLS_TEMPLATE_MD
