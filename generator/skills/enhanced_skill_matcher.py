"""Enhanced skill matcher using skill index with trigger-based matching."""

import json
import re
import fnmatch
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
import logging

logger = logging.getLogger(__name__)


class EnhancedSkillMatcher:
    """Match detected tech stack to relevant skills using trigger-based logic."""

    def __init__(self, skill_index_path: Optional[Path] = None):
        if skill_index_path is None:
            skill_index_path = Path(__file__).parent / 'skill_index.json'
        self.index = self._load_index(skill_index_path)

    def _load_index(self, path: Path) -> Dict:
        """Load the skill index JSON."""
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load skill index: {e}")
            return {'version': '1.0', 'skills': {}}

    def match_skills(
        self,
        detected_tech: List[str],
        project_context: Dict[str, Any],
    ) -> Set[str]:
        """
        Match detected tech stack and project context to relevant skills.

        Args:
            detected_tech: ['python', 'fastapi', 'pytest'] from metadata.tech_stack
            project_context: Full context from EnhancedProjectParser.extract_full_context()

        Returns:
            Set of skill paths to load, e.g.:
            {
                'builtin/code-review',
                'builtin/test-driven-development',
                'learned/fastapi/async-patterns',
                'learned/python-cli/argparse-patterns',
                'learned/pytest/coverage-patterns',
            }
        """
        selected: Set[str] = set()

        # Track whether ANY dependency-based trigger fired
        any_trigger_fired = False

        for tech in detected_tech:
            tech_key = self._normalize_tech_key(tech)
            tech_skills = self.index.get('skills', {}).get(tech_key, {})

            if not tech_skills:
                continue

            # Always add builtin skills for matched tech
            for builtin_name in tech_skills.get('builtin', []):
                selected.add(f'builtin/{builtin_name}')

            # Check triggers for learned skills
            triggers = tech_skills.get('triggers', [])
            if self._check_any_trigger(triggers, project_context):
                any_trigger_fired = True
                for skill_path in tech_skills.get('learned', []):
                    selected.add(f'learned/{skill_path}')

        # Fallback: if no triggers fired (e.g. 0 deps parsed), add learned
        # skills for all detected tech anyway — the tech was confirmed by
        # README detection, just not by dependency files.
        if not any_trigger_fired:
            for tech in detected_tech:
                tech_key = self._normalize_tech_key(tech)
                tech_skills = self.index.get('skills', {}).get(tech_key, {})
                for skill_path in tech_skills.get('learned', []):
                    selected.add(f'learned/{skill_path}')

        # Always include code-review as baseline
        selected.add('builtin/code-review')

        return selected

    def _normalize_tech_key(self, tech: str) -> str:
        """Normalize tech name to match skill index keys."""
        mappings = {
            'python': 'python-cli',
            'click': 'python-cli',
            'typer': 'python-cli',
            'argparse': 'python-cli',
            'fastapi': 'fastapi',
            'django': 'django',
            'flask': 'flask',
            'react': 'react',
            'vue': 'vue',
            'express': 'node',
            'koa': 'node',
            'pytest': 'pytest',
            'jest': 'jest',
            'docker': 'docker',
            'pytorch': 'ml-pipeline',
            'tensorflow': 'ml-pipeline',
            'sklearn': 'ml-pipeline',
            'transformers': 'ml-pipeline',
            'sqlalchemy': 'sqlalchemy',
            'celery': 'celery',
            'perplexity': 'api-integration',
            'groq': 'api-integration',
            'mistral': 'api-integration',
            'cohere': 'api-integration',
            'openai': 'api-integration',
            'anthropic': 'api-integration',
            'gemini': 'api-integration',
            'langchain': 'api-integration',
            'chrome': 'chrome-extension',
            'chrome-extension': 'chrome-extension',
            'gitpython': 'gitpython',
            'mcp': 'mcp',
            'httpx': 'api-integration',
            'aiohttp': 'api-integration',
            'requests': 'api-integration',
            'uvicorn': 'fastapi',
        }
        return mappings.get(tech.lower(), tech.lower())

    def _check_any_trigger(
        self,
        triggers: List[Dict],
        context: Dict[str, Any],
    ) -> bool:
        """Check if ANY trigger is satisfied (OR logic)."""
        for trigger in triggers:
            trigger_type = trigger.get('type', '')

            if trigger_type == 'import':
                if self._has_import(context, trigger.get('pattern', '')):
                    return True

            elif trigger_type == 'file':
                if self._has_file_pattern(context, trigger.get('pattern', '')):
                    return True

            elif trigger_type == 'dependency':
                if self._has_dependency(context, trigger.get('package', '')):
                    return True

        return False

    def _has_import(self, context: Dict, pattern: str) -> bool:
        """Check if any source file contains the import pattern."""
        structure = context.get('structure', {})
        entry_points = structure.get('entry_points', [])

        # Also check based on dependencies (if the package is installed, import is likely)
        deps = context.get('dependencies', {})
        python_names = {d['name'] for d in deps.get('python', [])}

        # Extract the module name from import pattern
        # e.g., "from fastapi import" -> "fastapi"
        match = re.search(r'(?:from|import)\s+(\w+)', pattern)
        if match:
            module = match.group(1).lower()
            if module in python_names:
                return True

        return False

    def _has_file_pattern(self, context: Dict, pattern: str) -> bool:
        """Check if project has files matching the pattern."""
        structure = context.get('structure', {})
        entry_points = structure.get('entry_points', [])
        detected_patterns = structure.get('patterns', [])

        # Simple filename match
        if '*' not in pattern and '/' not in pattern:
            # Direct filename check - entry_points contain relative paths
            for ep in entry_points:
                if Path(ep).name == pattern:
                    return True

        # Test framework files
        test_info = context.get('test_patterns', {})
        if pattern in ('conftest.py', 'test_*.py') and test_info.get('framework') == 'pytest':
            return True
        if pattern in ('jest.config.*', '*.test.js', '*.test.ts') and test_info.get('framework') == 'jest':
            return True

        # Docker files
        if pattern in ('Dockerfile', 'docker-compose.yml', 'docker-compose.yaml', '.dockerignore'):
            metadata = context.get('metadata', {})
            if metadata.get('has_docker', False):
                return True

        return False

    def _has_dependency(self, context: Dict, package: str) -> bool:
        """Check if a specific package is in the dependencies."""
        deps = context.get('dependencies', {})

        # Check Python deps
        for dep in deps.get('python', []):
            if dep.get('name', '').lower() == package.lower():
                return True

        # Check Node deps
        for dep in deps.get('node', []):
            if dep.get('name', '').lower() == package.lower():
                return True

        # Check dev deps too
        for dep in deps.get('python_dev', []):
            if dep.get('name', '').lower() == package.lower():
                return True
        for dep in deps.get('node_dev', []):
            if dep.get('name', '').lower() == package.lower():
                return True

        return False

    def get_skill_triggers(self, tech_key: str) -> List[Dict]:
        """Get triggers for a specific tech category."""
        return self.index.get('skills', {}).get(tech_key, {}).get('triggers', [])

    def list_all_tech_categories(self) -> List[str]:
        """List all tech categories in the index."""
        return list(self.index.get('skills', {}).keys())
