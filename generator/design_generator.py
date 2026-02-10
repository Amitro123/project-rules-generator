"""Technical design document generator (Stage 1 of two-stage planning)."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ArchitectureDecision(BaseModel):
    """A single architecture decision with trade-offs."""

    title: str = Field(description="Decision title, e.g. 'Auth Method'")
    choice: str = Field(description="Chosen approach, e.g. 'JWT tokens'")
    alternatives: List[str] = Field(default_factory=list, description="Rejected alternatives")
    pros: List[str] = Field(default_factory=list, description="Benefits of the choice")
    cons: List[str] = Field(default_factory=list, description="Drawbacks / risks")


class Design(BaseModel):
    """A complete technical design document."""

    title: str = Field(description="Design title")
    problem_statement: str = Field(description="What problem this solves")
    architecture_decisions: List[ArchitectureDecision] = Field(default_factory=list)
    api_contracts: List[str] = Field(default_factory=list, description="API endpoint specs")
    data_models: List[str] = Field(default_factory=list, description="Data model descriptions")
    success_criteria: List[str] = Field(default_factory=list, description="Definition of done")

    def to_markdown(self) -> str:
        """Render the design as a DESIGN.md markdown document."""
        lines = [
            f'# Design: {self.title}',
            '',
            '## Problem Statement',
            self.problem_statement,
            '',
        ]

        if self.architecture_decisions:
            lines += ['## Architecture Decisions', '']
            for dec in self.architecture_decisions:
                alt_str = f' (vs {", ".join(dec.alternatives)})' if dec.alternatives else ''
                lines.append(f'- **{dec.title}**: {dec.choice}{alt_str}')
                for pro in dec.pros:
                    lines.append(f'  - Pro: {pro}')
                for con in dec.cons:
                    lines.append(f'  - Con: {con}')
            lines.append('')

        if self.api_contracts:
            lines += ['## API Contracts', '']
            for contract in self.api_contracts:
                lines.append(f'- {contract}')
            lines.append('')

        if self.data_models:
            lines += ['## Data Models', '']
            for model in self.data_models:
                lines.append(f'- {model}')
            lines.append('')

        if self.success_criteria:
            lines += ['## Success Criteria', '']
            for criterion in self.success_criteria:
                lines.append(f'- {criterion}')
            lines.append('')

        return '\n'.join(lines)

    @classmethod
    def from_markdown(cls, text: str) -> 'Design':
        """Parse a DESIGN.md back into a Design object."""
        title = ''
        problem = ''
        decisions: List[ArchitectureDecision] = []
        api_contracts: List[str] = []
        data_models: List[str] = []
        success_criteria: List[str] = []

        # Extract title
        m = re.search(r'^#\s+Design:\s*(.+)', text, re.MULTILINE)
        if m:
            title = m.group(1).strip()

        # Split into sections by ## headings
        sections: Dict[str, str] = {}
        current_section = ''
        for line in text.split('\n'):
            if line.startswith('## '):
                current_section = line[3:].strip()
                sections[current_section] = ''
            elif current_section:
                sections[current_section] += line + '\n'

        problem = sections.get('Problem Statement', '').strip()

        # Parse architecture decisions
        arch_text = sections.get('Architecture Decisions', '')
        if arch_text:
            for m in re.finditer(
                r'-\s+\*\*(.+?)\*\*:\s*(.+?)(?=\n-\s+\*\*|\Z)',
                arch_text, re.DOTALL
            ):
                dec_title = m.group(1).strip()
                dec_body = m.group(2).strip()
                # Extract choice (before any " (vs ...)")
                choice_m = re.match(r'(.+?)(?:\s*\(vs\s+(.+?)\))?$', dec_body.split('\n')[0])
                choice = choice_m.group(1).strip() if choice_m else dec_body.split('\n')[0]
                alts = [a.strip() for a in choice_m.group(2).split(',')] if choice_m and choice_m.group(2) else []
                pros = re.findall(r'Pro:\s*(.+)', dec_body)
                cons = re.findall(r'Con:\s*(.+)', dec_body)
                decisions.append(ArchitectureDecision(
                    title=dec_title, choice=choice,
                    alternatives=alts, pros=pros, cons=cons,
                ))

        # Parse bullet lists
        api_contracts = _extract_bullets(sections.get('API Contracts', ''))
        data_models = _extract_bullets(sections.get('Data Models', ''))
        success_criteria = _extract_bullets(sections.get('Success Criteria', ''))

        return cls(
            title=title or 'Untitled Design',
            problem_statement=problem,
            architecture_decisions=decisions,
            api_contracts=api_contracts,
            data_models=data_models,
            success_criteria=success_criteria,
        )


def _extract_bullets(text: str) -> List[str]:
    """Pull top-level bullet items from markdown text."""
    return [m.group(1).strip() for m in re.finditer(r'^-\s+(.+)', text, re.MULTILINE)]


class DesignGenerator:
    """Generate a technical design document using AI or templates."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

    def generate_design(
        self,
        user_request: str,
        project_context: Optional[Dict] = None,
        project_path: Optional[Path] = None,
    ) -> Design:
        """Create a Design from a high-level user request.

        Uses AI when a key is available; otherwise returns a template-based design.
        """
        prompt = self._build_prompt(user_request, project_context, project_path)
        raw = self._call_llm(prompt)
        return self._parse_response(raw, user_request)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        user_request: str,
        project_context: Optional[Dict],
        project_path: Optional[Path],
    ) -> str:
        ctx_block = ''
        if project_context:
            meta = project_context.get('metadata', {})
            ctx_block = (
                f"\n## Project Context\n"
                f"- Type: {meta.get('project_type', 'unknown')}\n"
                f"- Tech: {', '.join(meta.get('tech_stack', []))}\n"
                f"- Has tests: {meta.get('has_tests', False)}\n"
            )
            structure = project_context.get('structure', {})
            if structure.get('entry_points'):
                ctx_block += f"- Entry points: {', '.join(structure['entry_points'])}\n"

        return f"""# Technical Design Generation

Create a technical design document for the following request.
Focus on architecture decisions with trade-offs, API contracts, data models, and success criteria.

## Request
{user_request}
{ctx_block}
## Output Format

Use this exact markdown structure:

# Design: <title>

## Problem Statement
<1-3 sentences describing what problem this solves>

## Architecture Decisions
- **<Decision Title>**: <chosen approach> (vs <alternative1>, <alternative2>)
  - Pro: <benefit>
  - Con: <drawback>

## API Contracts
- <METHOD> <path> -> <response shape>

## Data Models
- <ModelName>: <field1>, <field2>, ...

## Success Criteria
- <measurable criterion>

Generate the design now:
"""

    def _call_llm(self, prompt: str) -> str:
        if not self.api_key:
            return ''
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=3000,
                ),
            )
            return response.text
        except Exception:
            return ''

    def _parse_response(self, raw: str, user_request: str) -> Design:
        """Parse AI output into a Design. Falls back to template if empty."""
        if raw.strip():
            try:
                return Design.from_markdown(raw)
            except Exception:
                pass

        # Fallback: template-based design
        return Design(
            title=user_request[:80],
            problem_statement=user_request,
            architecture_decisions=[],
            api_contracts=[],
            data_models=[],
            success_criteria=[f'Implementation of: {user_request}'],
        )
