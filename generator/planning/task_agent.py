"""Task implementation agent — generates code changes for a subtask."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from generator.ai.factory import create_ai_client
from generator.exceptions import SecurityError
from generator.task_decomposer import SubTask

logger = logging.getLogger(__name__)

TASK_AGENT_SYSTEM_PROMPT = """You are an expert software engineer. 
Your task is to implement the changes described in the provided subtask.
You will receive the project context and the specific subtask details.
Respond with the exact code changes needed. 
Format your response as a list of file changes, each starting with [FILE: path/to/file] followed by the complete file content.
Example:
[FILE: src/main.py]
print("Hello World")

Only provide the files that need to be created or modified."""


class TaskImplementationAgent:
    """Agent that generates code changes for a subtask."""

    def __init__(self, provider: str = "groq", api_key: Optional[str] = None, client=None):
        self.client = client or create_ai_client(provider=provider, api_key=api_key)

    def implement(self, subtask: SubTask, project_context: Optional[Dict] = None) -> Dict[str, str]:
        """Generate file changes for a subtask.

        Returns a dict mapping file paths to their new content.
        """
        prompt = self._build_prompt(subtask, project_context)

        response = self.client.generate(
            prompt,
            temperature=0.2,
            max_tokens=4000,
            system_message=TASK_AGENT_SYSTEM_PROMPT,
        )

        return self._parse_response(response)

    def _build_prompt(self, subtask: SubTask, project_context: Optional[Dict]) -> str:
        ctx_str = ""
        if project_context:
            ctx_str = f"\nProject Context: {project_context.get('metadata', {})}"

        files_str = ", ".join(subtask.files) if subtask.files else "N/A"
        changes_str = "\n".join(f"- {c}" for c in subtask.changes) if subtask.changes else "N/A"
        tests_str = "\n".join(f"- {t}" for t in subtask.tests) if subtask.tests else "N/A"

        return f"""Implement the following subtask:
Task #{subtask.id}: {subtask.title}
Goal: {subtask.goal}
Files to Modify: {files_str}
Specific Changes:
{changes_str}
Tests to Verify:
{tests_str}
{ctx_str}
"""

    @staticmethod
    def _sanitize_path(raw: str) -> Optional[str]:
        """Validate and normalise an LLM-supplied file path.

        Accepts only relative paths with no ``..`` components.
        Returns the normalised POSIX-style path string, or ``None`` if the
        path is rejected (absolute, contains traversal, or empty).
        """
        raw = raw.strip()
        if not raw:
            return None

        try:
            p = Path(raw)
        except ValueError:
            logger.warning("Rejected malformed LLM file path: %r", raw)
            return None

        # Block absolute paths: pathlib covers Windows (C:\...) and Unix (/)
        # on their native platforms; the leading-slash check catches Unix-style
        # paths when running on Windows where Path("/foo").is_absolute() is False.
        if p.is_absolute() or raw.startswith("/") or raw.startswith("\\"):
            logger.warning("Rejected absolute LLM file path: %r", raw)
            return None

        # Block any path traversal component
        if any(part == ".." for part in p.parts):
            logger.warning("Rejected path-traversal LLM file path: %r", raw)
            return None

        # Return normalised, forward-slash form
        return p.as_posix()

    def _parse_response(self, response: str) -> Dict[str, str]:
        """Parse the AI response into a dict of {filepath: content}.

        Paths are validated by ``_sanitize_path``; invalid paths are logged
        and silently dropped so callers always receive a safe dict.
        """
        files: Dict[str, str] = {}
        current_file: Optional[str] = None
        current_content: List[str] = []

        for line in response.split("\n"):
            if line.startswith("[FILE:"):
                if current_file:
                    files[current_file] = "\n".join(current_content).strip()

                raw_path = line.replace("[FILE:", "").replace("]", "").strip()
                current_file = self._sanitize_path(raw_path)
                if current_file is None:
                    raise SecurityError(f"LLM returned unsafe file path: {raw_path!r}")
                current_content = []
            elif current_file:
                current_content.append(line)

        if current_file:
            files[current_file] = "\n".join(current_content).strip()

        return files
