"""Regression tests for pyproject.toml dependency detection.

The pyproject.toml branch must loop over PKG_MAP (like requirements.txt) so that
poetry-style projects — whose deps live only in [tool.poetry.dependencies] — are
not silently dropped. Regression: social-pulse kept `anthropic` only in poetry
deps and lost its profile-backed skill because the old code hardcoded checks for
just `fastapi` and `pytest`.
"""

from __future__ import annotations

from pathlib import Path

from generator.utils.tech_detector import detect_from_dependencies, detect_tech_stack


def _write_pyproject(tmp_path: Path, body: str) -> None:
    (tmp_path / "pyproject.toml").write_text(body, encoding="utf-8")


def test_poetry_dependencies_are_detected(tmp_path):
    """Deps declared only in [tool.poetry.dependencies] must be detected."""
    _write_pyproject(
        tmp_path,
        """
[tool.poetry]
name = "social-pulse"

[tool.poetry.dependencies]
python = "^3.10"
anthropic = "^0.7.0"
fastapi = "^0.100.0"
""",
    )

    detected = detect_from_dependencies(tmp_path)

    assert "anthropic" in detected
    assert "fastapi" in detected
    assert "python" in detected


def test_pep621_dependencies_are_detected(tmp_path):
    """PEP 621 [project] dependencies are covered by the same PKG_MAP scan."""
    _write_pyproject(
        tmp_path,
        """
[project]
name = "demo"
dependencies = ["pydantic>=2.0", "pytest>=8.0"]
""",
    )

    detected = detect_from_dependencies(tmp_path)

    assert "pydantic" in detected
    assert "pytest" in detected


def test_readme_prose_does_not_inject_unbacked_languages(tmp_path):
    """A Python project that only *describes* a JS frontend must not detect it.

    Regression: social-pulse's README mentioned "Node.js" / a planned JS frontend,
    which leaked `javascript` into the detected stack even though no .js/.ts source
    or package.json existed. Languages must come from real dependency/source files.
    """
    (tmp_path / "requirements.txt").write_text("fastapi\npydantic\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    readme = "Backend in Python. A JavaScript frontend (Node.js, React) is planned."

    detected = set(detect_tech_stack(tmp_path, readme))

    assert "python" in detected
    assert "fastapi" in detected
    assert "javascript" not in detected
    assert "typescript" not in detected


def test_real_typescript_sources_are_still_detected(tmp_path):
    """Languages backed by real source files must still be detected."""
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "App.tsx").write_text("export const App = () => null;\n", encoding="utf-8")

    detected = set(detect_tech_stack(tmp_path, "A FastAPI app with a TS frontend."))

    assert "typescript" in detected
