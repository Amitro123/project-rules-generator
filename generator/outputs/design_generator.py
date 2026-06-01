"""Technical design document generator (Stage 1 of two-stage planning)."""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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
            f"# Design: {self.title}",
            "",
            "## Problem Statement",
            self.problem_statement,
            "",
        ]

        if self.architecture_decisions:
            lines += ["## Architecture Decisions", ""]
            for dec in self.architecture_decisions:
                alt_str = f" (vs {', '.join(dec.alternatives)})" if dec.alternatives else ""
                lines.append(f"- **{dec.title}**: {dec.choice}{alt_str}")
                for pro in dec.pros:
                    lines.append(f"  - Pro: {pro}")
                for con in dec.cons:
                    lines.append(f"  - Con: {con}")
            lines.append("")

        if self.api_contracts:
            lines += ["## API Contracts", ""]
            for contract in self.api_contracts:
                lines.append(f"- {contract}")
            lines.append("")

        if self.data_models:
            lines += ["## Data Models", ""]
            for model in self.data_models:
                # Code blocks are stored verbatim; plain strings get a bullet prefix
                if model.startswith("```"):
                    lines.append(model)
                else:
                    lines.append(f"- {model}")
            lines.append("")

        if self.success_criteria:
            lines += ["## Success Criteria", ""]
            for criterion in self.success_criteria:
                lines.append(f"- {criterion}")
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, text: str) -> "Design":
        """Parse a DESIGN.md back into a Design object."""
        title = ""
        problem = ""
        decisions: List[ArchitectureDecision] = []
        api_contracts: List[str] = []
        data_models: List[str] = []
        success_criteria: List[str] = []

        # Extract title
        m = re.search(r"^#\s+Design:\s*(.+)", text, re.MULTILINE)
        if m:
            title = m.group(1).strip()

        # Split into sections by ## headings
        sections: Dict[str, str] = {}
        current_section = ""
        for line in text.split("\n"):
            if line.startswith("## "):
                current_section = line[3:].strip()
                sections[current_section] = ""
            elif current_section:
                sections[current_section] += line + "\n"

        problem = sections.get("Problem Statement", "").strip()

        # Parse architecture decisions
        arch_text = sections.get("Architecture Decisions", "")
        if arch_text:
            for m in re.finditer(r"-\s+\*\*(.+?)\*\*:\s*(.+?)(?=\n-\s+\*\*|\Z)", arch_text, re.DOTALL):
                dec_title = m.group(1).strip()
                dec_body = m.group(2).strip()
                # Extract choice (before any " (vs ...)")
                choice_m = re.match(r"(.+?)(?:\s*\(vs\s+(.+?)\))?$", dec_body.split("\n")[0])
                choice = choice_m.group(1).strip() if choice_m else dec_body.split("\n")[0]
                alts = [a.strip() for a in choice_m.group(2).split(",")] if choice_m and choice_m.group(2) else []
                pros = re.findall(r"Pro:\s*(.+)", dec_body)
                cons = re.findall(r"Con:\s*(.+)", dec_body)
                decisions.append(
                    ArchitectureDecision(
                        title=dec_title,
                        choice=choice,
                        alternatives=alts,
                        pros=pros,
                        cons=cons,
                    )
                )

        # Parse bullet lists; data_models may contain fenced code blocks
        api_contracts = _extract_bullets(sections.get("API Contracts", ""))
        data_models = _extract_code_blocks_or_bullets(sections.get("Data Models", ""))
        success_criteria = _extract_bullets(sections.get("Success Criteria", ""))

        return cls(
            title=title or "Untitled Design",
            problem_statement=problem,
            architecture_decisions=decisions,
            api_contracts=api_contracts,
            data_models=data_models,
            success_criteria=success_criteria,
        )


def _extract_bullets(text: str) -> List[str]:
    """Pull top-level bullet items from markdown text.

    Each bullet may span multiple lines; continuation lines are indented or
    start with optional whitespace but do NOT start with '- '.
    """
    items: List[str] = []
    current: List[str] = []
    for line in text.splitlines():
        if re.match(r"^-\s+", line):
            if current:
                items.append(" ".join(current))
            current = [line.lstrip("- ").strip()]
        elif current and line.strip() and not re.match(r"^#+\s", line):
            # continuation line of the current bullet
            current.append(line.strip())
        else:
            if current:
                items.append(" ".join(current))
                current = []
    if current:
        items.append(" ".join(current))
    return [item for item in items if item]


def _extract_code_blocks_or_bullets(text: str) -> List[str]:
    """Extract fenced code blocks from a section; fall back to bullets if none found."""
    blocks = re.findall(r"(```(?:\w+)?\n.*?```)", text, re.DOTALL)
    if blocks:
        return [b.strip() for b in blocks if b.strip()]
    return _extract_bullets(text)


class DesignGenerator:
    """Generate a technical design document using AI or templates."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: Optional[str] = "groq",
    ):
        """Initialize design generator with AI client.

        Args:
            api_key: Optional API key. When omitted, read from the environment
                variable for the chosen provider.
            model_name: Optional model name override.
            provider: AI provider — one of ``"groq"``, ``"gemini"``, ``"anthropic"``,
                ``"openai"``. Defaults to ``"groq"``. When ``None`` or ``"groq"``
                and ``GROQ_API_KEY`` is unset, auto-detects the first configured
                provider in preference order groq → gemini → anthropic → openai.
        """
        # Env-var resolution for every supported provider. Gemini accepts two
        # historical key names; the others are straightforward.
        _env_keys: Dict[str, Optional[str]] = {
            "groq": os.getenv("GROQ_API_KEY"),
            "gemini": os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "openai": os.getenv("OPENAI_API_KEY"),
        }

        # Auto-detect when the caller did not pin a provider.  Preference order
        # is groq first (free tier, fastest) then gemini, anthropic, openai —
        # matches the order advertised in the README.
        if provider is None or provider == "groq":
            selected: Optional[str] = None
            for candidate in ("groq", "gemini", "anthropic", "openai"):
                if _env_keys.get(candidate):
                    selected = candidate
                    break
            if selected is None:
                # No keys configured — keep the nominal default so errors surface
                # with a useful provider name rather than ``None``.
                self.provider = "groq"
                self.api_key = api_key
            else:
                self.provider = selected
                self.api_key = api_key or _env_keys[selected]
        else:
            self.provider = provider
            self.api_key = api_key or _env_keys.get(provider) or os.getenv(f"{provider.upper()}_API_KEY")

        # Only initialize AI client if an API key is available; otherwise fallback deterministically
        self.client: Optional[Any] = None
        try:
            from .ai.factory import create_ai_client

            if self.api_key:
                self.client = create_ai_client(self.provider, api_key=self.api_key)
                logger.debug("Design generator using: %s", self.provider)
            else:
                self.client = None
        except Exception as e:  # noqa: BLE001 — client init failure falls back to None (template mode)
            self.client = None
            logger.warning("Design AI client init failed: %s", e)

        self.model_name = model_name

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
        """Build a comprehensive prompt for production-quality design generation."""
        # Extract project context
        tech_stack = []
        project_type = "unknown"
        entry_points = []

        if project_context:
            meta = project_context.get("metadata", {})
            tech_stack = meta.get("tech_stack", [])
            project_type = meta.get("project_type", "unknown")
            structure = project_context.get("structure", {})
            entry_points = structure.get("entry_points", [])

        tech_str = ", ".join(tech_stack) if tech_stack else "Python"
        entry_str = ", ".join(entry_points[:3]) if entry_points else "N/A"

        return f"""You are a Senior Software Architect with 10+ years of experience in {tech_str}.

Generate a COMPLETE, PRODUCTION-READY technical design document for the following request.

## Request
{user_request}

## Project Context
- Type: {project_type}
- Tech Stack: {tech_str}
- Entry Points: {entry_str}

## Instructions

You MUST generate a comprehensive design with ALL of the following sections:

### 1. Problem Statement (2-3 sentences)
Clearly articulate what problem this solves and why it matters.

### 2. Architecture Decisions (3+ decisions)
For EACH decision, provide:
- Title of the decision
- Chosen approach
- 2-3 rejected alternatives
- 3+ pros of the chosen approach
- 2+ cons/risks of the chosen approach

Example decisions to consider:
- Technology choice (e.g., Redis vs Memcached, REST vs GraphQL)
- Design pattern (e.g., Repository pattern, Factory pattern)
- Data storage approach
- Error handling strategy
- Testing strategy

### 3. Data Models (2+ models)
Define Pydantic/dataclass models with:
- Model name
- All fields with types
- Validation rules
- Example usage

### 4. API Contracts (2+ functions/endpoints)
For EACH contract, specify:
- Function/endpoint signature
- Input parameters with types
- Return type
- Error cases
- Example call

### 5. Integration Points (2+ points)
Identify where this integrates with existing code:
- Which files to modify
- Which functions to call
- Error handling approach
- Backward compatibility considerations

### 6. Success Criteria (3+ metrics)
Define measurable success criteria:
- Performance metrics (e.g., "Response time < 100ms")
- Quality metrics (e.g., "Test coverage > 80%")
- Business metrics (e.g., "Cache hit rate > 80%")

### 7. Implementation Plan (5 steps)
Break down into concrete implementation steps:
1. Step with estimated time
2. Step with estimated time
...

## Output Format

Use this EXACT markdown structure:

# Design: <title>

## Problem Statement
<2-3 sentences>

## Architecture Decisions

- **<Decision 1 Title>**: <chosen approach> (vs <alt1>, <alt2>)
  - Pro: <benefit 1>
  - Pro: <benefit 2>
  - Pro: <benefit 3>
  - Con: <drawback 1>
  - Con: <drawback 2>

- **<Decision 2 Title>**: <chosen approach> (vs <alt1>, <alt2>)
  - Pro: <benefit>
  - Con: <drawback>

## Data Models

```python
class ModelName(BaseModel):
    field1: str = Field(description="...")
    field2: int = Field(ge=0)
    
    class Config:
        # validation config
```

## API Contracts

### `function_name(param1: Type1, param2: Type2) -> ReturnType`

**Purpose**: <what it does>

**Parameters**:
- `param1`: <description>
- `param2`: <description>

**Returns**: <description>

**Raises**:
- `ErrorType`: <when>

**Example**:
```python
result = function_name("value", 42)
```

## Integration Points

### File: `path/to/file.py`
- **Modify**: `existing_function()` to call new cache layer
- **Add**: Import statements for new models
- **Error handling**: Wrap in try/except, fallback to direct call

### File: `path/to/config.py`
- **Add**: Cache configuration settings

## Success Criteria

- **Performance**: Response time reduced by 50% (from 200ms to <100ms)
- **Reliability**: Cache hit rate > 80% after 1 hour of operation
- **Quality**: Test coverage > 85% for cache layer
- **Maintainability**: All public functions have docstrings

## Implementation Plan

1. **Create data models** (~30 min)
   - Define CacheConfig, CacheEntry models
   - Add validation logic
   - Write unit tests

2. **Implement cache client** (~1 hour)
   - Create cache wrapper class
   - Implement get/set/delete operations
   - Add error handling

3. **Integrate with existing code** (~45 min)
   - Modify API endpoints to use cache
   - Add cache middleware
   - Update configuration

4. **Write tests** (~1 hour)
   - Unit tests for cache operations
   - Integration tests for API endpoints
   - Performance benchmarks

5. **Documentation and deployment** (~30 min)
   - Update README with cache setup
   - Add configuration examples
   - Deploy to staging

**Total estimated time**: ~3.5 hours

---

NOW generate the complete design following this structure. Be specific, detailed, and production-ready.
"""

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with validator-driven retry.

        ``max_tokens=4000`` is a safe upper bound for the Groq free-tier Llama
        models (output cap ~6k); oversized requests previously caused silent
        mid-document truncation and an empty stub fallback.  Retries fire when
        the output is truncated or is missing the Success Criteria / Architecture
        Decisions sections — the failure modes users actually hit.
        """
        if not self.client:
            logger.warning("No AI client available")
            return ""
        from generator.ai.hardening import generate_with_validator, require_sections

        validator = require_sections("Success Criteria", "Architecture Decisions")
        result = generate_with_validator(
            self.client,
            prompt,
            validator=validator,
            max_tokens=4000,
            model=self.model_name,
            temperature=0.7,
            max_retries=1,
        )
        if not result or len(result.strip()) < 100:
            logger.warning("LLM returned short/empty response (%d chars)", len(result or ""))
        return result or ""

    def _parse_response(self, raw: str, user_request: str) -> Design:
        """Parse AI output into a Design. Falls back to the minimal stub if empty.

        When ``from_markdown`` raises on malformed output we still try to
        salvage the recognisable sections (title, success criteria,
        architecture decisions) before surrendering to the stub — a truncated
        response with 4 real success criteria is more useful than an empty
        placeholder document.
        """
        if not raw.strip():
            return self._generate_comprehensive_template(user_request)

        try:
            return Design.from_markdown(raw)
        except Exception as exc:  # noqa: BLE001 — malformed LLM output, attempt salvage
            logger.debug("Could not parse LLM output as Design markdown, attempting salvage: %s", exc)

        salvaged = self._salvage_partial_design(raw, user_request)
        if salvaged is not None:
            return salvaged

        return self._generate_comprehensive_template(user_request)

    @staticmethod
    def _salvage_partial_design(raw: str, user_request: str) -> Optional["Design"]:
        """Extract whatever sections are parseable from a malformed response.

        Runs the section-level regexes individually instead of the full
        ``from_markdown`` walker so a failure in one section (e.g. truncated
        Data Models) does not throw away a perfectly good Success Criteria
        block.  Returns ``None`` when nothing was recoverable.
        """
        sections: Dict[str, str] = {}
        current = ""
        for line in raw.split("\n"):
            if line.startswith("## "):
                current = line[3:].strip()
                sections[current] = ""
            elif current:
                sections[current] += line + "\n"

        title_match = re.search(r"^#\s+Design:\s*(.+)", raw, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else user_request.strip()

        problem = sections.get("Problem Statement", "").strip()
        criteria = _extract_bullets(sections.get("Success Criteria", ""))
        contracts = _extract_bullets(sections.get("API Contracts", ""))
        models = _extract_code_blocks_or_bullets(sections.get("Data Models", ""))

        if not any([problem, criteria, contracts, models]):
            return None

        logger.info(
            "Salvaged partial Design: problem=%s, criteria=%d, contracts=%d, models=%d",
            bool(problem),
            len(criteria),
            len(contracts),
            len(models),
        )
        return Design(
            title=title or "Untitled Design",
            problem_statement=problem
            or f"{user_request}\n\n> **Note:** LLM response was partial; some sections may be missing.",
            api_contracts=contracts,
            data_models=models,
            success_criteria=criteria,
        )

    def _generate_comprehensive_template(self, user_request: str) -> Design:
        """Minimal stub returned when AI is unavailable or LLM output cannot be parsed."""
        return Design(
            title=user_request.strip(),
            problem_statement=(
                f"{user_request}.\n\n"
                "> **Note:** AI provider unavailable — configure `GEMINI_API_KEY`, "
                "`ANTHROPIC_API_KEY`, or similar for a complete design."
            ),
        )
