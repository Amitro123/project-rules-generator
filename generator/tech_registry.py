"""
Tech Registry
=============

Single source of truth for all technology metadata.

Previously scattered across:
  - SkillGenerator.TECH_SKILL_NAMES   (skill_generator.py)
  - CoworkSkillCreator.TECH_TOOLS      (skill_creator.py)
  - CoworkRulesCreator.TECH_RULES      (rules_creator.py)
  - tech_keywords                      (utils/tech_detector.py)
  - pkg_map                            (utils/tech_detector.py)

Adding a new technology: add one TechProfile entry to _PROFILES below.
All derived dicts (TECH_SKILL_NAMES, PKG_MAP, …) are built automatically.
"""

from dataclasses import dataclass, field
from typing import Dict, List

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class TechProfile:
    """Complete metadata for one technology."""

    name: str
    """Canonical tech identifier (e.g. 'fastapi')."""

    skill_name: str = ""
    """Preferred skill filename stem (e.g. 'fastapi-endpoints'). Empty = no skill."""

    packages: List[str] = field(default_factory=list)
    """Package names in requirements.txt / pyproject.toml that signal this tech."""

    readme_keywords: List[str] = field(default_factory=list)
    """Keywords that appear in README prose to confirm detection."""

    tools: List[str] = field(default_factory=list)
    """CLI/shell tools associated with this tech (used in skill metadata)."""

    rules: Dict[str, List[str]] = field(default_factory=dict)
    """Coding rules keyed by priority: {'high': [...], 'medium': [...], 'low': [...]}."""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_PROFILES: List[TechProfile] = [
    # -- Web frameworks -------------------------------------------------------
    TechProfile(
        name="fastapi",
        skill_name="fastapi-endpoints",
        packages=["fastapi"],
        readme_keywords=["fastapi", "fast api"],
        tools=["uvicorn", "pydantic", "pytest", "httpx"],
        rules={
            "high": [
                "Use async/await for I/O operations (database, external APIs)",
                "Define Pydantic models for all request/response bodies",
                "Use Depends() for dependency injection (don't pass dependencies manually)",
                "Add response_model to all endpoints for validation",
            ],
            "medium": [
                "Use APIRouter for modular route organization",
                "Add OpenAPI tags and descriptions to endpoints",
                "Implement proper exception handlers with HTTPException",
                "Use BackgroundTasks for non-blocking operations",
            ],
            "low": [
                "Add request/response examples in docstrings",
                "Use status codes from fastapi.status module",
            ],
        },
    ),
    TechProfile(
        name="flask",
        skill_name="flask-routes",
        packages=["flask"],
        readme_keywords=["flask"],
        tools=["flask", "pytest", "requests"],
    ),
    TechProfile(
        name="django",
        skill_name="django-views",
        packages=["django"],
        readme_keywords=["django"],
        tools=["django", "pytest", "django-admin"],
    ),
    TechProfile(
        name="express",
        skill_name="express-routes",
        packages=[],
        readme_keywords=["express", "expressjs"],
    ),
    # -- Frontend -------------------------------------------------------------
    TechProfile(
        name="react",
        skill_name="react-components",
        packages=[],
        readme_keywords=["react", "reactjs", "react.js"],
        tools=["npm", "webpack", "jest", "eslint"],
        rules={
            "high": [
                "Use functional components with hooks (not class components)",
                "Keep components pure - avoid side effects in render",
                "Use useCallback/useMemo for expensive computations",
                "Avoid prop drilling - use Context or state management",
            ],
            "medium": [
                "Split large components into smaller, reusable ones",
                "Use custom hooks to extract reusable logic",
                "Implement error boundaries for graceful failures",
                "Use React.lazy() for code splitting",
            ],
            "low": [
                "Add PropTypes or TypeScript for type safety",
                "Use React DevTools for debugging",
            ],
        },
    ),
    TechProfile(
        name="vue",
        skill_name="vue-components",
        packages=[],
        readme_keywords=["vue", "vuejs", "vue.js"],
        tools=["npm", "vue-cli", "jest"],
    ),
    # -- Testing --------------------------------------------------------------
    TechProfile(
        name="pytest",
        skill_name="pytest-testing",
        packages=["pytest"],
        readme_keywords=["pytest"],
        tools=["pytest", "coverage", "pytest-cov"],
        rules={
            "high": [
                "Use fixtures for test setup/teardown (don't repeat setup)",
                "Parametrize tests with @pytest.mark.parametrize",
                "Mock external dependencies (APIs, databases)",
            ],
            "medium": [
                "Organize tests in tests/ mirroring source structure",
                "Use conftest.py for shared fixtures",
                "Add docstrings explaining what each test validates",
            ],
            "low": [
                "Use pytest.raises() for exception testing",
                "Add markers (@pytest.mark.slow) for test categories",
            ],
        },
    ),
    TechProfile(
        name="jest",
        skill_name="jest-testing",
        packages=[],
        readme_keywords=["jest"],
    ),
    # -- Infrastructure -------------------------------------------------------
    TechProfile(
        name="docker",
        skill_name="docker-deployment",
        packages=["docker"],
        readme_keywords=["docker", "dockerfile", "docker-compose"],
        tools=["docker", "docker-compose"],
        rules={
            "high": [
                "Use multi-stage builds to minimize image size",
                "Don't run containers as root (use USER directive)",
                "Pin specific versions in base images (not :latest)",
            ],
            "medium": [
                "Use .dockerignore to exclude unnecessary files",
                "Set health checks with HEALTHCHECK directive",
                "Use docker-compose for multi-container setups",
            ],
        },
    ),
    TechProfile(
        name="kubernetes",
        skill_name="",
        packages=[],
        readme_keywords=["kubernetes", "k8s"],
        tools=["kubectl", "helm"],
    ),
    # -- Async / messaging ----------------------------------------------------
    TechProfile(
        name="asyncio",
        skill_name="",
        packages=[],
        readme_keywords=["asyncio", "async"],
        rules={
            "high": [
                "Always use async/await (not callbacks or futures)",
                "Don't mix blocking and async code in same function",
                "Use asyncio.gather() for concurrent operations",
            ],
            "medium": [
                "Implement proper exception handling in async tasks",
                "Use asyncio.create_task() for fire-and-forget operations",
                "Add timeouts to async operations (asyncio.wait_for)",
            ],
        },
    ),
    TechProfile(
        name="celery",
        skill_name="celery-tasks",
        packages=["celery"],
        readme_keywords=["celery"],
        tools=["redis-cli", "celery"],
    ),
    # -- Databases ------------------------------------------------------------
    TechProfile(
        name="sqlalchemy",
        skill_name="sqlalchemy-models",
        packages=["sqlalchemy"],
        readme_keywords=["sqlalchemy"],
        tools=["alembic", "pytest"],
        rules={
            "high": [
                "Use async SQLAlchemy for async frameworks",
                "Always use sessions properly (with context manager)",
                "Define relationships with lazy='selectin' to avoid N+1",
            ],
            "medium": [
                "Use Alembic for database migrations",
                "Add indexes on frequently queried columns",
                "Implement soft deletes for critical data",
            ],
        },
    ),
    TechProfile(
        name="redis",
        skill_name="redis-caching",
        packages=["redis"],
        readme_keywords=["redis"],
        tools=["redis-cli"],
    ),
    TechProfile(
        name="mongodb",
        skill_name="mongodb-queries",
        packages=["pymongo", "motor"],
        readme_keywords=["mongodb", "mongo"],
    ),
    TechProfile(
        name="postgresql",
        skill_name="postgresql-queries",
        packages=["psycopg2", "psycopg2-binary", "asyncpg"],
        readme_keywords=["postgresql", "postgres"],
        tools=["psql", "pg_dump"],
    ),
    # -- ML / AI --------------------------------------------------------------
    TechProfile(
        name="pytorch",
        skill_name="pytorch-training",
        packages=["torch"],
        readme_keywords=["pytorch", "torch"],
    ),
    TechProfile(
        name="tensorflow",
        skill_name="tensorflow-models",
        packages=["tensorflow"],
        readme_keywords=["tensorflow"],
    ),
    TechProfile(
        name="openai",
        skill_name="openai-api",
        packages=["openai"],
        readme_keywords=["openai", "gpt-4", "gpt-3"],
        tools=["pytest", "ruff", "mypy"],
    ),
    TechProfile(
        name="anthropic",
        skill_name="claude-cowork-workflow",
        packages=["anthropic"],
        readme_keywords=["anthropic", "claude"],
        tools=["pytest", "ruff", "mypy"],
    ),
    TechProfile(
        name="groq",
        skill_name="groq-api",
        packages=["groq"],
        readme_keywords=["groq"],
        tools=["pytest", "ruff", "mypy"],
        rules={
            "high": [
                "Always use the GroqClient wrapper — never call the Groq API directly",
                "Set GROQ_API_KEY via environment variable, never hardcode",
                "Handle groq.RateLimitError with exponential backoff retry",
            ],
            "medium": [
                "Use llama-3.1-8b-instant for fast tasks, llama-3.3-70b for quality",
                "Log token usage per request for cost monitoring",
                "Implement provider fallback: Groq -> Gemini on failure",
            ],
        },
    ),
    TechProfile(
        name="gemini",
        skill_name="gemini-api",
        packages=["google-generativeai", "google-genai"],
        readme_keywords=["gemini", "google ai"],
        tools=["pytest", "ruff", "mypy"],
        rules={
            "high": [
                "Always use the GeminiClient wrapper — never call the Gemini API directly",
                "Set GEMINI_API_KEY via environment variable, never hardcode",
                "Handle google.api_core.exceptions.ResourceExhausted with retry",
            ],
            "medium": [
                "Use gemini-2.0-flash for speed, gemini-1.5-pro for complex reasoning",
                "Implement provider fallback: Gemini -> Groq on quota exhaustion",
                "Log model name and token count for every API call",
            ],
        },
    ),
    TechProfile(
        name="perplexity",
        skill_name="perplexity-api",
        packages=["perplexity"],
        readme_keywords=["perplexity", "sonar"],
    ),
    TechProfile(
        name="langchain",
        skill_name="langchain-chains",
        packages=["langchain"],
        readme_keywords=["langchain"],
        tools=["pytest", "ruff"],
    ),
    # -- CLI / validation / templates -----------------------------------------
    TechProfile(
        name="click",
        skill_name="click-cli",
        packages=["click"],
        readme_keywords=["click"],
        rules={
            "high": [
                "Keep @click.command() functions thin — delegate business logic to core modules",
                "Use click.testing.CliRunner for all CLI integration tests",
                "Always set exit codes explicitly: sys.exit(0) success, sys.exit(1) failure",
                "Use click.echo() for output, never print() directly in command functions",
            ],
            "medium": [
                "Group related commands with @click.group() and register in a dedicated CLI module",
                "Add --verbose / -v flag to every command for debug output",
                "Use click.Path(exists=True) for path arguments to validate early",
                "Add help strings to every @click.option() and @click.argument()",
            ],
            "low": [
                "Use click.confirm() for destructive operations",
                "Add epilog= to commands showing usage examples",
            ],
        },
    ),
    TechProfile(
        name="typer",
        skill_name="typer-cli",
        packages=["typer"],
        readme_keywords=["typer"],
    ),
    TechProfile(
        name="pydantic",
        skill_name="pydantic-validation",
        packages=["pydantic"],
        readme_keywords=["pydantic"],
        rules={
            "high": [
                "Define Pydantic models for all structured data (not raw dicts)",
                "Use Field() with description= for self-documenting models",
                "Validate at the boundary — parse input into models as early as possible",
            ],
            "medium": [
                "Use model_validator for cross-field validation logic",
                "Prefer model.model_dump() over dict() (Pydantic v2)",
                "Use Optional[X] = None for truly optional fields, not X = None",
            ],
            "low": [
                "Add json_schema_extra for OpenAPI documentation hints",
            ],
        },
    ),
    TechProfile(
        name="jinja2",
        skill_name="",
        packages=["jinja2"],
        readme_keywords=["jinja2", "jinja"],
        rules={
            "high": [
                "Store all templates in templates/ with .jinja2 extension",
                "Never build markdown/HTML by string concatenation — use templates",
                "Use Environment(autoescape=False) for markdown templates (not HTML)",
            ],
            "medium": [
                "Pass only the data the template needs — avoid passing full objects",
                "Use {%- and -%} to control whitespace in generated output",
                "Test template rendering in unit tests with known fixture data",
            ],
        },
    ),
    # -- HTTP clients ---------------------------------------------------------
    TechProfile(
        name="httpx",
        skill_name="httpx-client",
        packages=["httpx"],
        readme_keywords=["httpx"],
    ),
    TechProfile(
        name="requests",
        skill_name="requests-client",
        packages=["requests"],
        readme_keywords=["requests"],
    ),
    TechProfile(
        name="aiohttp",
        skill_name="aiohttp-client",
        packages=["aiohttp"],
        readme_keywords=["aiohttp"],
    ),
    # -- Networking / protocols -----------------------------------------------
    TechProfile(
        name="websocket",
        skill_name="websocket-handler",
        packages=["websockets"],
        readme_keywords=["websocket", "websockets"],
    ),
    TechProfile(
        name="graphql",
        skill_name="graphql-schema",
        packages=[],
        readme_keywords=["graphql"],
    ),
    # -- Server / DevOps tools ------------------------------------------------
    TechProfile(
        name="uvicorn",
        skill_name="uvicorn-server",
        packages=["uvicorn"],
        readme_keywords=["uvicorn"],
    ),
    TechProfile(
        name="git",
        skill_name="",
        packages=[],
        readme_keywords=["git"],
        tools=["git"],
    ),
    TechProfile(
        name="gitpython",
        skill_name="gitpython-ops",
        packages=["gitpython"],
        readme_keywords=["gitpython", "git diff", "git operations"],
    ),
    # -- Specialised / canvas / DXF -------------------------------------------
    TechProfile(
        name="dxf",
        skill_name="dxf-processing",
        packages=["ezdxf"],
        readme_keywords=["dxf", "ezdxf", "dxf editor", "dxf upload", "dxf viewer"],
    ),
    TechProfile(
        name="konva",
        skill_name="konva-nesting-canvas",
        packages=["konva"],
        readme_keywords=["konva", "konvajs", "konva.js"],
    ),
    TechProfile(
        name="canvas",
        skill_name="konva-nesting-canvas",
        packages=[],
        readme_keywords=["canvas", "svg canvas", "html canvas"],
    ),
    TechProfile(
        name="threejs",
        skill_name="threejs-scene",
        packages=[],
        readme_keywords=["three.js", "threejs", "three js", "webgl", "3d extrusion"],
    ),
    TechProfile(
        name="babylon",
        skill_name="babylon-scene",
        packages=[],
        readme_keywords=["babylon", "babylonjs", "babylon.js"],
    ),
    TechProfile(
        name="supabase",
        skill_name="supabase-auth-storage",
        packages=["supabase"],
        readme_keywords=["supabase"],
    ),
    TechProfile(
        name="reportlab",
        skill_name="reportlab-pdf",
        packages=["reportlab"],
        readme_keywords=["reportlab"],
    ),
    TechProfile(
        name="pdf",
        skill_name="reportlab-pdf",
        packages=[],
        readme_keywords=["pdf", "pdf generation", "pdf export"],
    ),
    # -- Browser extension ----------------------------------------------------
    TechProfile(
        name="chrome",
        skill_name="chrome-extension",
        packages=[],
        readme_keywords=["chrome", "chrome extension", "manifest.json"],
    ),
    # -- MCP / model context protocol -----------------------------------------
    TechProfile(
        name="mcp",
        skill_name="mcp-protocol",
        packages=[],
        readme_keywords=["mcp", "model context protocol", "mcp server"],
    ),
    # -- Languages (detection-only, no skill) ---------------------------------
    TechProfile(
        name="python",
        skill_name="",
        packages=[],
        readme_keywords=["python"],
    ),
    TechProfile(
        name="typescript",
        skill_name="",
        packages=[],
        readme_keywords=["typescript"],
    ),
    TechProfile(
        name="javascript",
        skill_name="",
        packages=[],
        readme_keywords=["javascript", "node.js", "nodejs"],
    ),
    TechProfile(
        name="go",
        skill_name="",
        packages=[],
        readme_keywords=["golang", "go lang"],
    ),
    TechProfile(
        name="rust",
        skill_name="",
        packages=[],
        readme_keywords=["rust", "rustlang", "cargo"],
    ),
]

# ---------------------------------------------------------------------------
# Derived lookups (all built once at module load)
# ---------------------------------------------------------------------------

REGISTRY: Dict[str, TechProfile] = {p.name: p for p in _PROFILES}

# tech name → preferred skill filename
TECH_SKILL_NAMES: Dict[str, str] = {p.name: p.skill_name for p in _PROFILES if p.skill_name}
# Also include legacy aliases that pointed to the same skill
TECH_SKILL_NAMES["websockets"] = "websocket-handler"
TECH_SKILL_NAMES["chrome-extension"] = "chrome-extension"

# tech name → list of shell tools
TECH_TOOLS: Dict[str, List[str]] = {p.name: p.tools for p in _PROFILES if p.tools}

# tech name → coding rules {priority: [rules]}
TECH_RULES: Dict[str, Dict[str, List[str]]] = {p.name: p.rules for p in _PROFILES if p.rules}

# tech name → list of README keywords
TECH_README_KEYWORDS: Dict[str, List[str]] = {p.name: p.readme_keywords for p in _PROFILES if p.readme_keywords}

# package name → canonical tech name  (inverse of TechProfile.packages)
PKG_MAP: Dict[str, str] = {}
for _p in _PROFILES:
    for _pkg in _p.packages:
        PKG_MAP[_pkg] = _p.name
