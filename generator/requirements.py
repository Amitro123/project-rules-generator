"""Requirement inference engine — extracts project requirements from multiple sources."""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from generator.ai.ai_client import create_ai_client

@dataclass
class Requirement:
    """A discrete project requirement."""
    id: str
    description: str
    source: str  # "README", "spec.md", "Git", "Code"
    priority: int = 3  # 1 (Highest) to 5 (Lowest)
    status: str = "pending"

class RequirementsInferrer:
    """Infers project requirements from documentation, history, and code."""

    def __init__(self, provider: str = "groq", api_key: Optional[str] = None, client=None):
        self.client = client or create_ai_client(provider=provider, api_key=api_key)

    def infer(self, project_path: Path) -> List[Requirement]:
        """Synthesize requirements from all available sources."""
        project_path = Path(project_path).resolve()
        requirements = []

        # 1. README
        readme_path = project_path / "README.md"
        if readme_path.exists():
            requirements.extend(self._analyze_readme(readme_path))

        # 2. Git History
        requirements.extend(self._analyze_git_history(project_path))

        # 3. Code Analysis (TODOs, endpoints)
        requirements.extend(self._analyze_codebase(project_path))
        
        # 4. Synthesize/De-duplicate with AI
        return self._synthesize(requirements)

    def _analyze_readme(self, path: Path) -> List[Requirement]:
        """Extract features/stories from README using heuristics or simple parsing."""
        content = path.read_text(encoding="utf-8")
        requirements = []
        
        # Look for "Features" or "How it works" sections
        sections = re.findall(r"##\s+(?:Features|How It Works|Usage)(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
        for section in sections:
            bullets = re.findall(r"-\s+(.+)", section)
            for b in bullets:
                requirements.append(Requirement(
                    id=f"feat-{len(requirements)+1}",
                    description=b.strip(),
                    source="README",
                    priority=2
                ))
        return requirements

    def _analyze_git_history(self, project_path: Path) -> List[Requirement]:
        """Extract recent evolution from git log."""
        try:
            result = subprocess.run(
                ["git", "-C", str(project_path), "log", "--oneline", "-50"],
                capture_output=True,
                text=True,
                check=True
            )
            logs = result.stdout.splitlines()
            # Simple heuristic: commits with "feat:", "add", "fix"
            requirements = []
            for log in logs:
                if any(x in log.lower() for x in ["feat:", "add", "implement"]):
                    requirements.append(Requirement(
                        id=f"git-{len(requirements)+1}",
                        description=log.split(" ", 1)[1],
                        source="Git",
                        priority=3
                    ))
            return requirements
        except Exception:
            return []

    def _analyze_codebase(self, project_path: Path) -> List[Requirement]:
        """Find TODOs and endpoints in the codebase."""
        requirements = []
        
        # 1. Search for TODOs
        try:
            # Using grep-like search via subprocess if path is large, or just glob
            for p in project_path.rglob("*.py"):
                if ".clinerules" in str(p) or "venv" in str(p):
                    continue
                content = p.read_text(encoding="utf-8", errors="ignore")
                todos = re.findall(r"(?:#|//)\s*TODO:\s*(.+)", content, re.IGNORECASE)
                for t in todos:
                    requirements.append(Requirement(
                        id=f"code-{len(requirements)+1}",
                        description=f"TODO in {p.name}: {t.strip()}",
                        source="Code",
                        priority=4
                    ))
        except Exception:
            pass
            
        return requirements

    def _synthesize(self, requirements: List[Requirement]) -> List[Requirement]:
        """Use AI to de-duplicate and refine the requirement list."""
        if not requirements:
            return []

        req_list = "\n".join([f"- [{r.source}] {r.description}" for r in requirements])
        
        prompt = f"""Below is a raw list of potential requirements gathered from README, Git, and Code analysis.
Refine this into a clean, de-duplicated list of atomic project requirements.
Group similar ones, fix ambiguity, and assign a priority (1-5).

Raw Requirements:
{req_list}

Respond in this exact format:
ID: [id]
DESC: [description]
PRIORITY: [1-5]
SOURCE: [Original source]
---
"""
        
        response = self.client.generate(
            prompt,
            temperature=0.3,
            system_message="You are a senior requirements engineer. Synthesize and de-duplicate project requirements."
        )
        
        # Encoding Safety: Clean response
        text = response.encode('utf-8', errors='replace').decode('utf-8')
        text = text.replace('ג€”', '—').replace('ג', '')
        
        return self._parse_synthesized(text)

    def _parse_synthesized(self, response: str) -> List[Requirement]:
        refined = []
        blocks = response.split("---")
        for block in blocks:
            if "ID:" not in block: continue
            try:
                id_val = re.search(r"ID:\s*(.+)", block).group(1).strip()
                desc = re.search(r"DESC:\s*(.+)", block).group(1).strip()
                pri = re.search(r"PRIORITY:\s*(\d+)", block).group(1).strip()
                src = re.search(r"SOURCE:\s*(.+)", block).group(1).strip()
                refined.append(Requirement(
                    id=id_val,
                    description=desc,
                    source=src,
                    priority=int(pri)
                ))
            except Exception:
                continue
        return refined
