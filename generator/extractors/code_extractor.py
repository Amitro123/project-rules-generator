"""Extract relevant code examples from the project using AST parsing."""

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Directories to skip
SKIP_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".tox",
    ".mypy_cache",
    ".eggs",
    "htmlcov",
}


class CodeExampleExtractor:
    """Extract relevant code examples from the project."""

    # Mapping from skill topics to things to look for
    TOPIC_PATTERNS = {
        "fastapi": {
            "decorators": [
                "app.get",
                "app.post",
                "app.put",
                "app.delete",
                "router.get",
                "router.post",
            ],
            "imports": ["fastapi", "pydantic"],
            "classes": ["BaseModel", "FastAPI"],
        },
        "validation": {
            "decorators": ["validator", "field_validator", "model_validator"],
            "imports": ["pydantic"],
            "classes": ["BaseModel", "Field"],
        },
        "auth": {
            "decorators": ["Depends"],
            "imports": ["jwt", "oauth2", "security", "auth"],
            "functions": ["get_current_user", "authenticate", "login", "verify_token"],
        },
        "async": {
            "keywords": ["async def", "await", "asyncio"],
            "imports": ["asyncio", "aiohttp", "httpx"],
        },
        "testing": {
            "decorators": ["pytest.fixture", "pytest.mark"],
            "imports": ["pytest", "unittest", "mock"],
            "functions": ["test_"],
        },
        "cli": {
            "decorators": [
                "click.command",
                "click.option",
                "click.argument",
                "click.group",
            ],
            "imports": ["click", "argparse", "typer"],
            "classes": ["ArgumentParser"],
        },
        "database": {
            "imports": ["sqlalchemy", "alembic", "peewee", "tortoise"],
            "classes": ["Base", "Model", "Column", "Table"],
            "functions": ["create_engine", "sessionmaker"],
        },
        "error-handling": {
            "keywords": ["try:", "except ", "raise ", "HTTPException"],
            "classes": ["Exception", "HTTPException", "ValidationError"],
        },
    }

    def extract_examples_for_skill(
        self,
        project_path: Path,
        skill_topic: str,
        tech_stack: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Find code examples relevant to the skill topic.

        Returns:
            [
                {
                    'file': 'src/api/models.py',
                    'line': 15,
                    'code': 'class UserCreate(BaseModel): ...',
                    'type': 'class',
                    'is_good_example': True,
                    'reason': 'Uses Pydantic validators',
                }
            ]
        """
        examples = []
        project_path = Path(project_path)

        # Determine what to look for based on skill topic
        search_patterns = self._get_search_patterns(skill_topic, tech_stack)

        # Find relevant source files
        source_files = self._get_source_files(project_path)

        for source_file in source_files:
            try:
                file_examples = self._extract_from_file(
                    source_file, project_path, search_patterns
                )
                examples.extend(file_examples)
            except Exception as e:
                logger.debug(f"Failed to extract from {source_file}: {e}")

            # Limit total examples
            if len(examples) >= 10:
                break

        # Sort by relevance (good examples first, then by specificity)
        examples.sort(
            key=lambda x: (not x.get("is_good_example", True), -x.get("relevance", 0))
        )

        return examples[:10]

    def _get_search_patterns(
        self,
        skill_topic: str,
        tech_stack: List[str],
    ) -> Dict[str, List[str]]:
        """Determine what patterns to search for based on skill topic."""
        patterns: Dict[str, List[str]] = {
            "decorators": [],
            "imports": [],
            "classes": [],
            "functions": [],
            "keywords": [],
        }

        # Normalize topic
        topic_lower = skill_topic.lower().replace("-", " ")
        topic_parts = set(topic_lower.split())

        # Match against known topic patterns
        for topic_key, topic_patterns in self.TOPIC_PATTERNS.items():
            if topic_key in topic_lower or topic_key in topic_parts:
                for key in patterns:
                    if key in topic_patterns:
                        patterns[key].extend(topic_patterns[key])

        # Add patterns from tech stack
        for tech in tech_stack:
            tech_lower = tech.lower()
            if tech_lower in self.TOPIC_PATTERNS:
                topic_patterns = self.TOPIC_PATTERNS[tech_lower]
                for key in patterns:
                    if key in topic_patterns:
                        patterns[key].extend(topic_patterns[key])

        # If nothing matched, use generic patterns from the topic name
        if not any(patterns.values()):
            topic_words = skill_topic.replace("-", "_").split("_")
            patterns["imports"] = topic_words
            patterns["functions"] = topic_words

        return patterns

    def _extract_from_file(
        self,
        file_path: Path,
        project_path: Path,
        search_patterns: Dict[str, List[str]],
    ) -> List[Dict[str, Any]]:
        """Extract examples from a single Python file using AST."""
        examples = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return examples

        relative_path = str(file_path.relative_to(project_path))
        lines = content.splitlines()

        # Try AST parsing for Python files
        if file_path.suffix == ".py":
            examples.extend(
                self._extract_with_ast(content, lines, relative_path, search_patterns)
            )

        # Fallback: regex-based extraction for all file types
        examples.extend(
            self._extract_with_regex(content, lines, relative_path, search_patterns)
        )

        # Deduplicate by line number
        seen_lines = set()
        unique_examples = []
        for ex in examples:
            if ex["line"] not in seen_lines:
                seen_lines.add(ex["line"])
                unique_examples.append(ex)

        return unique_examples

    def _extract_with_ast(
        self,
        content: str,
        lines: List[str],
        relative_path: str,
        search_patterns: Dict[str, List[str]],
    ) -> List[Dict[str, Any]]:
        """Extract examples using Python AST parsing."""
        examples = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return examples

        for node in ast.walk(tree):
            # Function definitions
            if isinstance(node, ast.FunctionDef) or isinstance(
                node, ast.AsyncFunctionDef
            ):
                func_name = node.name
                is_async = isinstance(node, ast.AsyncFunctionDef)

                # Check if function matches any pattern
                for pattern in search_patterns.get("functions", []):
                    if pattern.lower() in func_name.lower():
                        code_snippet = self._extract_snippet(lines, node.lineno - 1, 10)
                        examples.append(
                            {
                                "file": relative_path,
                                "line": node.lineno,
                                "code": code_snippet,
                                "type": "async_function" if is_async else "function",
                                "name": func_name,
                                "is_good_example": True,
                                "reason": f"{'Async f' if is_async else 'F'}unction matching '{pattern}'",
                                "relevance": 5,
                            }
                        )
                        break

                # Check decorators
                for decorator in node.decorator_list:
                    dec_str = self._decorator_to_string(decorator)
                    for pattern in search_patterns.get("decorators", []):
                        if pattern.lower() in dec_str.lower():
                            code_snippet = self._extract_snippet(
                                lines, node.lineno - 1, 10
                            )
                            examples.append(
                                {
                                    "file": relative_path,
                                    "line": node.lineno,
                                    "code": code_snippet,
                                    "type": "decorated_function",
                                    "name": func_name,
                                    "is_good_example": True,
                                    "reason": f"Uses @{dec_str}",
                                    "relevance": 7,
                                }
                            )
                            break

            # Class definitions
            elif isinstance(node, ast.ClassDef):
                class_name = node.name
                for pattern in search_patterns.get("classes", []):
                    # Check class name or base classes
                    base_names = [self._name_to_string(b) for b in node.bases]
                    if pattern.lower() in class_name.lower() or any(
                        pattern.lower() in b.lower() for b in base_names
                    ):
                        code_snippet = self._extract_snippet(lines, node.lineno - 1, 12)
                        examples.append(
                            {
                                "file": relative_path,
                                "line": node.lineno,
                                "code": code_snippet,
                                "type": "class",
                                "name": class_name,
                                "is_good_example": True,
                                "reason": f"Class {'inheriting ' + pattern if base_names else 'matching ' + pattern}",
                                "relevance": 6,
                            }
                        )
                        break

            # Import statements
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                module = ""
                if isinstance(node, ast.ImportFrom) and node.module:
                    module = node.module
                elif isinstance(node, ast.Import):
                    module = ", ".join(alias.name for alias in node.names)

                for pattern in search_patterns.get("imports", []):
                    if pattern.lower() in module.lower():
                        code_snippet = (
                            lines[node.lineno - 1].strip()
                            if node.lineno <= len(lines)
                            else ""
                        )
                        examples.append(
                            {
                                "file": relative_path,
                                "line": node.lineno,
                                "code": code_snippet,
                                "type": "import",
                                "name": module,
                                "is_good_example": True,
                                "reason": f"Imports {module}",
                                "relevance": 2,
                            }
                        )
                        break

        return examples

    def _extract_with_regex(
        self,
        content: str,
        lines: List[str],
        relative_path: str,
        search_patterns: Dict[str, List[str]],
    ) -> List[Dict[str, Any]]:
        """Regex-based extraction as fallback."""
        examples = []

        for keyword in search_patterns.get("keywords", []):
            for i, line in enumerate(lines):
                if keyword.lower() in line.lower():
                    code_snippet = self._extract_snippet(lines, i, 5)
                    examples.append(
                        {
                            "file": relative_path,
                            "line": i + 1,
                            "code": code_snippet,
                            "type": "keyword_match",
                            "name": keyword,
                            "is_good_example": True,
                            "reason": f"Contains '{keyword}'",
                            "relevance": 3,
                        }
                    )
                    if len(examples) >= 3:  # Limit regex matches per file
                        break

        return examples

    @staticmethod
    def _extract_snippet(lines: List[str], start_line: int, max_lines: int = 10) -> str:
        """Extract a code snippet from the given line range."""
        end = min(start_line + max_lines, len(lines))
        snippet_lines = lines[start_line:end]
        return "\n".join(snippet_lines)

    @staticmethod
    def _decorator_to_string(decorator: ast.expr) -> str:
        """Convert a decorator AST node to string representation."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            parts = []
            node = decorator
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))
        elif isinstance(decorator, ast.Call):
            return CodeExampleExtractor._decorator_to_string(decorator.func)
        return ""

    @staticmethod
    def _name_to_string(node: ast.expr) -> str:
        """Convert an AST name node to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""

    @staticmethod
    def _get_source_files(project_path: Path) -> List[Path]:
        """Get source files to analyze, sorted by likely relevance."""
        files = []
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx"}

        for f in project_path.rglob("*"):
            if f.suffix not in extensions:
                continue
            # Skip irrelevant directories
            if any(skip in f.parts for skip in SKIP_DIRS):
                continue
            files.append(f)
            if len(files) >= 100:
                break

        # Sort: prefer non-test files, prefer shorter paths (more central)
        files.sort(
            key=lambda f: (
                "test" in f.name.lower(),
                len(f.parts),
                f.name,
            )
        )

        return files
