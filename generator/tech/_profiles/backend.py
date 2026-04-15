"""Backend TechProfile entries: web frameworks, async, CLI, HTTP clients, networking, specialised."""

from typing import List

from generator.tech.profile import TechProfile

BACKEND: List[TechProfile] = [
    # -- Web frameworks -------------------------------------------------------
    TechProfile(
        name="fastapi",
        display_name="FastAPI",
        category="backend",
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
        display_name="Flask",
        category="backend",
        skill_name="flask-routes",
        packages=["flask"],
        readme_keywords=["flask"],
        tools=["flask", "pytest", "requests"],
    ),
    TechProfile(
        name="django",
        display_name="Django",
        category="backend",
        skill_name="django-views",
        packages=["django"],
        readme_keywords=["django"],
        tools=["django", "pytest", "django-admin"],
    ),
    TechProfile(
        name="express",
        display_name="Express",
        category="backend",
        skill_name="express-routes",
        packages=["express"],
        readme_keywords=["express", "expressjs"],
    ),
    # -- Async / messaging ----------------------------------------------------
    TechProfile(
        name="asyncio",
        display_name="asyncio",
        category="backend",
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
        display_name="Celery",
        category="backend",
        skill_name="celery-tasks",
        packages=["celery"],
        readme_keywords=["celery"],
        tools=["redis-cli", "celery"],
    ),
    # -- CLI / validation / templates -----------------------------------------
    TechProfile(
        name="click",
        display_name="Click",
        category="backend",
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
        display_name="Typer",
        category="backend",
        skill_name="typer-cli",
        packages=["typer"],
        readme_keywords=["typer"],
    ),
    TechProfile(
        name="pydantic",
        display_name="Pydantic",
        category="backend",
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
        display_name="Jinja2",
        category="backend",
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
    TechProfile(
        name="rich",
        display_name="rich",
        category="backend",
        skill_name="",
        packages=["rich"],
        readme_keywords=["rich"],
    ),
    TechProfile(
        name="gitpython",
        display_name="GitPython",
        category="backend",
        skill_name="gitpython-ops",
        packages=["gitpython"],
        readme_keywords=["gitpython", "git diff", "git operations"],
        import_name="git",
    ),
    TechProfile(
        name="whisper",
        display_name="Whisper",
        category="backend",
        skill_name="",
        packages=["openai-whisper", "whisper"],
        readme_keywords=["whisper", "speech recognition"],
    ),
    TechProfile(
        name="reportlab",
        display_name="ReportLab",
        category="backend",
        skill_name="reportlab-pdf",
        packages=["reportlab"],
        readme_keywords=["reportlab"],
    ),
    TechProfile(
        name="pdf",
        display_name="PDF",
        category="backend",
        skill_name="reportlab-pdf",
        packages=[],
        readme_keywords=["pdf", "pdf generation", "pdf export"],
    ),
    TechProfile(
        name="mcp",
        display_name="MCP",
        category="backend",
        skill_name="mcp-protocol",
        packages=[],
        readme_keywords=["mcp", "model context protocol", "mcp server"],
    ),
    # -- HTTP clients ---------------------------------------------------------
    TechProfile(
        name="httpx",
        display_name="HTTPX",
        category="backend",
        skill_name="httpx-client",
        packages=["httpx"],
        readme_keywords=["httpx"],
    ),
    TechProfile(
        name="requests",
        display_name="Requests",
        category="backend",
        skill_name="requests-client",
        packages=["requests"],
        readme_keywords=["requests"],
    ),
    TechProfile(
        name="aiohttp",
        display_name="aiohttp",
        category="backend",
        skill_name="aiohttp-client",
        packages=["aiohttp"],
        readme_keywords=["aiohttp"],
    ),
    # -- Networking / protocols -----------------------------------------------
    TechProfile(
        name="websocket",
        display_name="WebSocket",
        category="backend",
        skill_name="websocket-handler",
        packages=["websockets"],
        readme_keywords=["websocket", "websockets"],
    ),
    TechProfile(
        name="graphql",
        display_name="GraphQL",
        category="backend",
        skill_name="graphql-schema",
        packages=[],
        readme_keywords=["graphql"],
    ),
    # -- Specialised ----------------------------------------------------------
    TechProfile(
        name="dxf",
        display_name="DXF",
        category="backend",
        skill_name="dxf-processing",
        packages=["ezdxf"],
        readme_keywords=["dxf", "ezdxf", "dxf editor", "dxf upload", "dxf viewer"],
    ),
]
