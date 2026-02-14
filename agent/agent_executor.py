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
        user_input_lower = user_input.lower()

        # Simple keyword matching for now
        # Could be enhanced with fuzzy matching or embeddings later

        best_match = None
        max_overlap = (
            0  # Not typically useful for simple phrase match, but maybe for partials?
        )

        # We look for exact phrase usage mostly
        for skill, phrases in self._triggers.items():
            for phrase in phrases:
                # remove quotes if present in phrase
                clean_phrase = phrase.strip("\"'").lower()

                # print(f"DEBUG: Checking '{clean_phrase}' in '{user_input_lower}'")
                if clean_phrase in user_input_lower:
                    # Found a match!
                    return skill

        return None
