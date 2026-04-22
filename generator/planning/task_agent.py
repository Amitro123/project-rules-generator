"""Task implementation agent — generates code changes for a subtask."""

import logging
import re
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

Format your response as a list of file changes, each starting with
[FILE: <relative path from project root>] followed by the complete file content.

CRITICAL path rules:
- Use ONLY directories that exist in the Project Structure section of the
  prompt. Do not invent `src/` unless `src/` is listed there.
- Paths must be relative to the project root and use forward slashes.
- Do not emit absolute paths, Windows drive letters, or `..` traversal.

Example (generic placeholder — replace `<pkg>` with a real project directory):
[FILE: <pkg>/module.py]
<file content here>

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
            rules = project_context.get("rules_context") or project_context.get("metadata") or ""
            if rules:
                ctx_str = f"\nProject Rules & Context:\n{rules}"

            # Pass the real project tree through to the agent so [FILE: ...]
            # paths are grounded in what actually exists.
            project_path = project_context.get("project_path")
            if project_path:
                try:
                    from generator.utils.readme_bridge import build_project_tree

                    path_obj = project_path if isinstance(project_path, Path) else Path(project_path)
                    if path_obj.is_dir():
                        tree = build_project_tree(path_obj, max_depth=3, max_items=60)
                        ctx_str += f"\nProject Structure (use THESE directories):\n```\n{tree[:1200]}\n```\n"
                except Exception as exc:  # noqa: BLE001 — tree build is best-effort
                    logger.debug("Could not build project tree for task agent prompt: %s", exc)

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

        Treats all input as untrusted/hostile regardless of the host OS.
        Steps:
          1. Normalize backslashes → forward slashes so Windows-style paths
             from LLM output are handled identically on Linux and Windows.
          2. Reject Windows drive letters (``C:/``) and UNC/network paths
             (``//server``).  pathlib alone is insufficient because
             ``Path("C:/foo").is_absolute()`` is False on Linux.
          3. Reject leading slashes (absolute Unix paths).
          4. Split and rebuild from safe components only — empty segments,
             ``.`` , and ``..`` are stripped or trigger rejection.

        Returns the normalised POSIX-style relative path string, or ``None``
        if the path is rejected.
        """
        raw = raw.strip()
        if not raw:
            return None

        # Step 1: normalize separators — must happen before any pattern checks
        normalized = raw.replace("\\", "/")

        # Step 2: reject Windows drive letters (C:/, D:/) and UNC paths (//host)
        if re.match(r"^[a-zA-Z]:/", normalized):
            logger.warning("Rejected Windows drive path from LLM: %r", raw)
            return None
        if normalized.startswith("//"):
            logger.warning("Rejected UNC/network path from LLM: %r", raw)
            return None

        # Step 3: reject absolute Unix-style paths
        if normalized.startswith("/"):
            logger.warning("Rejected absolute path from LLM: %r", raw)
            return None

        # Step 4: rebuild from safe components — reject on traversal
        safe_parts: List[str] = []
        for part in normalized.split("/"):
            part = part.strip()
            if part == "..":
                logger.warning("Rejected path-traversal from LLM: %r", raw)
                return None
            if not part or part == ".":
                continue  # skip empty segments and redundant current-dir markers
            safe_parts.append(part)

        if not safe_parts:
            return None

        return "/".join(safe_parts)

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
