"""Template management with lazy loading"""
from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache

# Tech specific templates remain in code as they are small snippets
TECH_SPECIFIC_SKILLS = {
    'react': """
### react-expert
Analyze and refactor React components using best practices.

**When to use:**
- Complex state management logic
- Performance optimization (memoization)
- Component reusability analysis

**Checks:**
- Hook dependency arrays
- Prop drilling issues
- Component composition
""",
    'vue': """
### vue-expert
Analyze Vue 2/3 components and Composition API usage.

**When to use:**
- Refactoring Options API to Composition API
- Reactivity debugging
- Store (Pinia/Vuex) optimization
""",
    'fastapi': """
### fastapi-security-auditor
Check FastAPI endpoints for common security issues.

**When to use:**
- Adding new authenticated endpoints
- Reviewing dependency injection
- Pydantic model validation
""",
    'docker': """
### docker-optimizer
Optimize Dockerfile and compose configurations.

**When to use:**
- Slow build times
- Large image sizes
- Container security scanning
"""
}

# Base location for external markdown templates
TEMPLATE_DIR = Path(__file__).parent.parent / 'templates' / 'skills'

@lru_cache(maxsize=10)
def load_skill_template(project_type: str) -> str:
    """
    Load skill template from file (cached).
    
    Args:
        project_type: One of: agent, ml_pipeline, web_app, cli_tool, library, generator
        
    Returns:
        Template content as string
        
    Raises:
        FileNotFoundError: If template doesn't exist
    """
    if not TEMPLATE_DIR.exists():
        # Fallback if directory structure differs (e.g. running from different root)
        # Try finding it relative to this file
        local_template_dir = Path(__file__).parent.parent / 'templates' / 'skills'
        if local_template_dir.exists():
            template_path = local_template_dir / f"{project_type}.md"
        else:
             raise FileNotFoundError(f"Template directory not found at {TEMPLATE_DIR}")
    else:
        template_path = TEMPLATE_DIR / f"{project_type}.md"
    
    if not template_path.exists():
        # Return empty string or default fallback instead of crashing hard?
        # For now, let's return empty but log warning if we had logging
        return "" 
    
    return template_path.read_text(encoding='utf-8')


def get_all_available_templates() -> Dict[str, str]:
    """Get all available template types."""
    if not TEMPLATE_DIR.exists():
        return {}
    
    return {
        path.stem: load_skill_template(path.stem)
        for path in TEMPLATE_DIR.glob('*.md')
    }

class SkillTemplates:
    """Wrapper class for skills to maintain backwards compatibility if needed"""
    @staticmethod
    def get(project_type: str, default: str = "") -> str:
        content = load_skill_template(project_type)
        return content if content else default

SKILL_TEMPLATES = SkillTemplates()
