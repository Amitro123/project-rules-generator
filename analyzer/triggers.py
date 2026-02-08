from pathlib import Path
from typing import List, Dict, Any, Set
import re
import fnmatch
from generator.types import Skill

class SkillTriggerDetector:
    """
    Detects which skills should be active based on project context
    and skill auto-trigger definitions.
    """
    
    def __init__(self, project_path: Path, project_context: Dict[str, Any]):
        self.project_path = project_path
        self.context = project_context
        self._cache_file_list: List[str] = []
        self._load_file_list()

    def _load_file_list(self):
        """Cache list of files for pattern matching."""
        # Walk project, respect gitignore if possible (simple walk for now)
        # Limit depth to avoid massive scan
        try:
            for root, dirs, files in self.project_path.walk(): # python 3.12+
                 # Skip common ignored
                if '.git' in dirs: dirs.remove('.git')
                if 'node_modules' in dirs: dirs.remove('node_modules')
                if 'venv' in dirs: dirs.remove('venv')
                
                rel_root = root.relative_to(self.project_path)
                for file in files:
                    self._cache_file_list.append(str(rel_root / file).replace('\\', '/'))
        except AttributeError:
             # Fallback for older python
            for root, dirs, files in os.walk(self.project_path):
                if '.git' in dirs: dirs.remove('.git')
                if 'node_modules' in dirs: dirs.remove('node_modules')
                rel_root = Path(root).relative_to(self.project_path)
                for file in files:
                    self._cache_file_list.append(str(rel_root / file).replace('\\', '/'))
        except Exception:
            pass
            
    def _get_tech_stack_set(self) -> Set[str]:
        """Extract tech stack as a flat set of lowercase strings."""
        ts = self.context.get('tech_stack', [])
        if isinstance(ts, dict):
            # Flatten dict values
            flat_list = sum(ts.values(), [])
            return {t.lower() for t in flat_list}
        elif isinstance(ts, list):
            return {str(t).lower() for t in ts}
        return set()

    def match_skill(self, skill: Skill) -> List[str]:
        """
        Check if skill should be triggered.
        Returns list of matched conditions (empty if not triggered).
        """
        matched_conditions = []
        
        # 1. Check structured auto_triggers (List[Dict])
        if skill.auto_triggers:
            for trigger_group in skill.auto_triggers:
                if self._check_trigger_group(trigger_group, matched_conditions):
                    return matched_conditions

        # 2. Check legacy list triggers (List[str] - keywords)
        # These are usually just keywords like "fastapi" or "python"
        if skill.triggers:
            # Check against tech stack
            tech_stack_lower = self._get_tech_stack_set()
            
            for trigger in skill.triggers:
                if trigger.lower() in tech_stack_lower:
                    matched_conditions.append(f"Matched tech: {trigger}")
                    
        return matched_conditions

    def _check_trigger_group(self, group: Dict[str, Any], results: List[str]) -> bool:
        """
        Check a single trigger group (AND logic).
        All defined criteria in the group must match.
        """
        matches = []
        
        # 1. Keywords (Tech Stack or file content?)
        # Let's match against Tech Stack for now
        if 'keywords' in group:
            tech_stack_lower = self._get_tech_stack_set()
            
            for kw in group['keywords']:
                if kw.lower() not in tech_stack_lower:
                    return False # Fail
                matches.append(f"Keyword: {kw}")

        # 2. File Patterns
        if 'file_patterns' in group:
            for pattern in group['file_patterns']:
                if not any(fnmatch.fnmatch(f, pattern) for f in self._cache_file_list):
                    return False # Fail
                matches.append(f"File Pattern: {pattern}")

        # 3. Project Signals (structure analysis)
        if 'project_signals' in group:
            structure = self.context.get('structure', {})
            for signal in group['project_signals']:
                # signal names map to structure keys (e.g. "has_docker")
                if not structure.get(signal, False):
                    return False
                matches.append(f"Signal: {signal}")

        # If we got here, all conditions in this group passed
        results.extend(matches)
        return True

import os
