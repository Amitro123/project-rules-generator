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

        # Parse bullet lists
        api_contracts = _extract_bullets(sections.get("API Contracts", ""))
        data_models = _extract_bullets(sections.get("Data Models", ""))
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


class DesignGenerator:
    """Generate a technical design document using AI or templates."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: str = "groq",
    ):
        """Initialize design generator with AI client.

        Args:
            api_key: Optional API key (auto-detects from environment)
            model_name: Optional model name override
            provider: AI provider ('gemini' or 'groq'), defaults to 'groq'
        """
        # Auto-detect provider if not explicitly set
        _gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if provider is None or provider == "groq":
            # Default to Groq to avoid API key errors
            if os.getenv("GROQ_API_KEY"):
                self.provider = "groq"
                self.api_key = api_key or os.getenv("GROQ_API_KEY")
            elif _gemini_key:
                self.provider = "gemini"
                self.api_key = api_key or _gemini_key
            else:
                self.provider = "groq"
                self.api_key = api_key
        else:
            self.provider = provider
            if provider == "gemini":
                self.api_key = api_key or _gemini_key
            else:
                self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")

        # Only initialize AI client if an API key is available; otherwise fallback deterministically
        self.client: Optional[Any] = None
        try:
            from .ai.factory import create_ai_client

            if self.api_key:
                self.client = create_ai_client(self.provider, api_key=self.api_key)
                logger.debug("Design generator using: %s", self.provider)
            else:
                self.client = None
        except Exception as e:
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
        if not self.client:
            logger.warning("No AI client available")
            return ""
        try:
            result = self.client.generate(prompt, max_tokens=8000, model=self.model_name, temperature=0.7)
            if not result or len(result.strip()) < 100:
                logger.warning("LLM returned short/empty response (%d chars)", len(result))
            return result
        except Exception as e:
            logger.error("Error calling LLM: %s", e)
            return ""

    def _parse_response(self, raw: str, user_request: str) -> Design:
        """Parse AI output into a Design. Falls back to comprehensive template if empty."""
        if raw.strip():
            try:
                return Design.from_markdown(raw)
            except Exception as exc:
                logger.debug("Could not parse LLM output as Design markdown, using template fallback: %s", exc)

        # Fallback: Generate comprehensive template-based design
        # This demonstrates production-quality output structure
        return self._generate_comprehensive_template(user_request)

    def _generate_comprehensive_template(self, user_request: str) -> Design:
        """Generate a comprehensive design template when AI is unavailable.

        This creates a production-quality design structure that demonstrates
        all the sections a senior architect would include.
        """
        # Extract key terms from request for customization
        text = user_request.lower()
        is_cache = ("cache" in text) or ("redis" in text)
        is_auth = ("auth" in text) or ("authentication" in text) or ("login" in text)

        # Create comprehensive architecture decisions
        decisions = []

        if is_cache:
            decisions.append(
                ArchitectureDecision(
                    title="Cache Technology",
                    choice="Redis",
                    alternatives=["Memcached", "In-memory dict", "Database caching"],
                    pros=[
                        "Persistent storage with configurable TTL",
                        "Rich data structures (strings, hashes, lists, sets)",
                        "Built-in pub/sub for cache invalidation",
                        "Widely adopted with strong Python support (redis-py)",
                    ],
                    cons=[
                        "Additional infrastructure dependency",
                        "Network latency for cache operations",
                        "Requires monitoring and maintenance",
                    ],
                )
            )
            decisions.append(
                ArchitectureDecision(
                    title="Cache Strategy",
                    choice="Cache-aside pattern",
                    alternatives=["Write-through", "Write-behind"],
                    pros=[
                        "Application controls cache logic explicitly",
                        "Cache failures don't break the application",
                        "Easy to implement and reason about",
                    ],
                    cons=[
                        "Potential cache stampede on cold start",
                        "Requires manual cache invalidation logic",
                    ],
                )
            )
        else:
            decisions.append(
                ArchitectureDecision(
                    title="Implementation Approach",
                    choice="Modular design with dependency injection",
                    alternatives=["Monolithic implementation", "Microservice"],
                    pros=[
                        "Testable components with clear interfaces",
                        "Easy to mock dependencies in tests",
                        "Flexible for future changes",
                    ],
                    cons=[
                        "More upfront design work",
                        "Slightly more complex initial setup",
                    ],
                )
            )

        decisions.append(
            ArchitectureDecision(
                title="Error Handling",
                choice="Graceful degradation with fallback",
                alternatives=["Fail fast", "Retry with exponential backoff"],
                pros=[
                    "System remains available even if component fails",
                    "Better user experience during partial outages",
                    "Easier to debug with clear error paths",
                ],
                cons=[
                    "May mask underlying issues",
                    "Requires careful logging to track degraded states",
                ],
            )
        )

        # Create data models
        data_models = []
        if is_cache:
            data_models.append("""```python
class CacheConfig(BaseModel):
    \"\"\"Configuration for cache layer.\"\"\"
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0)
    ttl_seconds: int = Field(default=3600, ge=60, description="Default TTL")
    max_retries: int = Field(default=3, ge=0)
    
    class Config:
        frozen = True  # Immutable config
```""")
            data_models.append("""```python
class CacheEntry(BaseModel):
    \"\"\"Represents a cached value with metadata.\"\"\"
    key: str
    value: Any
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl: int = Field(ge=0)
    
    def is_expired(self) -> bool:
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl
```""")
        else:
            data_models.append(f"""```python
class {user_request.split()[0].title()}Config(BaseModel):
    \"\"\"Configuration for {user_request}.\"\"\"
    enabled: bool = Field(default=True)
    timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)
```""")

        # Create API contracts
        api_contracts = []
        if is_cache:
            api_contracts.append("""### `get_cached(key: str, fetch_fn: Callable[[], T]) -> T`

**Purpose**: Retrieve value from cache or fetch and cache it

**Parameters**:
- `key`: Cache key (string)
- `fetch_fn`: Function to call if cache miss

**Returns**: Cached or freshly fetched value

**Raises**:
- `CacheError`: If cache operation fails
- `ValueError`: If key is invalid

**Example**:
```python
def fetch_user(user_id: int) -> User:
    return db.query(User).get(user_id)

user = get_cached(f"user:{user_id}", lambda: fetch_user(user_id))
```""")
            api_contracts.append("""### `invalidate_cache(pattern: str) -> int`

**Purpose**: Remove cache entries matching pattern

**Parameters**:
- `pattern`: Redis key pattern (supports wildcards)

**Returns**: Number of keys deleted

**Example**:
```python
# Invalidate all user caches
count = invalidate_cache("user:*")
```""")
        else:
            api_contracts.append(f"""### `execute_{user_request.split()[0].lower()}(params: dict) -> Result`

**Purpose**: Execute the {user_request} operation

**Parameters**:
- `params`: Operation parameters

**Returns**: Operation result

**Raises**:
- `ValidationError`: If params are invalid
- `OperationError`: If execution fails
""")

        # Create success criteria
        criteria = []
        if is_cache:
            criteria.extend(
                [
                    "**Performance**: API response time reduced by 50% (from 200ms to <100ms)",
                    "**Reliability**: Cache hit rate > 80% after 1 hour of operation",
                    "**Quality**: Test coverage > 85% for cache layer",
                    "**Maintainability**: All public functions have comprehensive docstrings",
                ]
            )
        else:
            criteria.extend(
                [
                    f"**Functionality**: {user_request} works as specified",
                    "**Quality**: Test coverage > 80%",
                    "**Performance**: Operation completes in < 1 second",
                    "**Maintainability**: Code follows project style guide",
                ]
            )

        # Ensure title preserves key domain terms capitalization like "Authentication"
        title = user_request.strip()
        if is_auth and "authentication" in text and "Authentication" not in title:
            # Capitalize the keyword for readability in title
            title = re.sub(r"authentication", "Authentication", title, flags=re.IGNORECASE)

        return Design(
            title=title,
            problem_statement=f"{user_request}. This enhancement will improve system performance, reliability, and user experience by implementing a robust, well-tested solution following industry best practices.",
            architecture_decisions=decisions,
            api_contracts=api_contracts,
            data_models=data_models,
            success_criteria=criteria,
        )
