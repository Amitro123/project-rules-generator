import json
from pathlib import Path
from typing import Dict, List, Optional


class AgentExecutor:
    """Handles agent-related tasks like auto-triggering skills."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.triggers_path = project_path / ".clinerules" / "auto-triggers.json"
        self._triggers: Dict[str, List[str]] = {}
        self._load_triggers()

    def _load_triggers(self):
        """Load triggers from JSON if available."""
        if self.triggers_path.exists():
            try:
                content = self.triggers_path.read_text(encoding="utf-8")
                self._triggers = json.loads(content)
            except Exception as e:
                print(f"[Warning] Failed to load auto-triggers: {e}")

    def match_skill(self, user_input: str) -> Optional[str]:
        """
        Find the best matching skill for the user input.
        Returns the skill name or None.
        """
        if not self._triggers:
            print(f"[DEBUG] No triggers loaded from {self.triggers_path}")
            return None

        print(f"[DEBUG] Loaded {len(self._triggers)} trigger groups.")
        user_input_lower = user_input.lower()

        # Simple keyword matching for now
        # Could be enhanced with fuzzy matching or embeddings later

        # We look for exact phrase usage mostly
        for skill, phrases in self._triggers.items():
            for phrase in phrases:
                # remove quotes if present in phrase
                clean_phrase = phrase.strip("\"'").lower()

                print(f"[DEBUG] Checking '{clean_phrase}' in '{user_input_lower}'")
                if clean_phrase in user_input_lower:
                    # Found a match!
                    # Verify skill exists in learned (standard location) or builtin
                    # We assume standard structure now: .clinerules/skills/learned/<skill>/SKILL.md or .md
                    skill_path = self.project_path / ".clinerules" / "skills" / "learned" / skill
                    flat_path = self.project_path / ".clinerules" / "skills" / "learned" / f"{skill}.md"
                    
                    if skill_path.exists() or flat_path.exists():
                        print(f"[DEBUG] MATCH FOUND for skill: {skill}")
                        return skill
                    else:
                        print(f"[DEBUG] Trigger matched but skill '{skill}' not found in .clinerules/skills/learned")
                        # Fallback to just returning it? Or scanning builtin?
                        # For now, let's trust the trigger but warn
                        return skill

        print("[DEBUG] No match found.")
        return None
