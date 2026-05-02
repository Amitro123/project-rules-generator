"""Detect architecture patterns from file/folder structure."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Directories to skip during analysis
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
    "*.egg-info",
    "htmlcov",
    ".coverage",
}


class StructureAnalyzer:
    """Detect architecture patterns from file/folder structure."""

    # Per-pattern minimum score threshold.  The default is 2 (any two signals).
    # Framework patterns that require stronger evidence (e.g. flask-app, django-app)
    # need at least 4 points so that a single helper-file import doesn't mis-classify
    # a project whose primary framework is something else entirely.
    PATTERN_THRESHOLDS: Dict[str, int] = {
        "flask-app": 4,    # Requires folder evidence OR multiple file imports
        "django-app": 4,   # Same — manage.py alone isn't enough
    }

    PATTERNS = {
        "python-cli": {
            "markers": ["__main__.py", "argparse", "click", "typer", "fire"],
            "folders": ["src/cli", "src/commands", "commands", "cli"],
            "files": ["cli.py", "__main__.py", "main.py"],
            "imports": [
                r"import argparse",
                r"import click",
                r"import typer",
                r"from click import",
            ],
        },
        "fastapi-api": {
            "markers": ["from fastapi import", "app = FastAPI()", "FastAPI()"],
            "folders": ["src/api", "src/routes", "api", "routes", "routers"],
            "files": ["app.py", "server.py"],
            "imports": [
                r"from fastapi import",
                r"import fastapi",
                r"app\s*=\s*FastAPI\(",
            ],
        },
        "django-app": {
            "markers": ["django", "manage.py", "wsgi.py", "asgi.py"],
            "folders": ["templates", "static", "migrations"],
            "files": ["manage.py", "wsgi.py", "asgi.py", "settings.py"],
            "imports": [r"import django", r"from django", r"DJANGO_SETTINGS_MODULE"],
        },
        "flask-app": {
            "markers": ["from flask import", "Flask(__name__)"],
            "folders": ["templates", "static", "blueprints"],
            "files": [],
            "imports": [r"from flask import", r"import flask", r"Flask\(__name__\)"],
        },
        "react-app": {
            "markers": ["App.jsx", "App.tsx", "react"],
            "folders": ["src/components", "public", "src/hooks", "src/pages"],
            "files": ["App.jsx", "App.tsx", "index.jsx", "index.tsx"],
            "imports": [r'from ["\']react["\']', r"import React"],
        },
        "vue-app": {
            "markers": ["App.vue", "vue"],
            "folders": ["src/components", "src/views", "src/store"],
            "files": ["App.vue", "main.js", "main.ts"],
            "imports": [r'from ["\']vue["\']', r"createApp"],
        },
        "node-api": {
            "markers": ["express", "koa", "hapi"],
            "folders": ["routes", "controllers", "middleware", "models"],
            "files": ["server.js", "server.ts", "index.js", "app.js"],
            "imports": [
                r'require\(["\']express',
                r'from ["\']express',
                r'from ["\']koa',
            ],
        },
        "ml-pipeline": {
            "markers": ["pytorch", "tensorflow", "sklearn", "transformers"],
            "folders": ["models", "data", "notebooks", "training", "inference"],
            "files": ["train.py", "model.py", "dataset.py", "predict.py"],
            "imports": [
                r"import torch",
                r"import tensorflow",
                r"from sklearn",
                r"from transformers",
            ],
        },
        "library": {
            "markers": ["setup.py", "pyproject.toml"],
            "folders": ["src", "docs", "examples"],
            "files": ["setup.py", "setup.cfg"],
            "imports": [],
        },
    }

    TEST_PATTERNS = {
        "pytest": {
            "markers": ["pytest", "conftest.py"],
            # pyproject.toml omitted here (too broad — Rust/Node projects use it too).
            # Content-based detection via config_keys handles pyproject.toml correctly.
            "files": ["conftest.py", "tests/conftest.py", "pytest.ini"],
            "imports": [r"import pytest", r"from pytest"],
            "config_keys": ["[tool.pytest", "[pytest"],
            # Also match pytest listed as a dep name (e.g. Poetry dev-dependencies)
            "dep_patterns": [r"^\s*pytest\s*[=<>\^\~!\[]"],
        },
        "unittest": {
            "markers": ["unittest"],
            "files": [],
            "imports": [r"import unittest", r"from unittest"],
            "config_keys": [],
        },
        "jest": {
            "markers": ["jest"],
            "files": ["jest.config.js", "jest.config.ts"],
            "imports": [r"describe\(", r"it\(", r"expect\("],
            "config_keys": ['"jest"'],
        },
        "mocha": {
            "markers": ["mocha"],
            "files": [".mocharc.yml", ".mocharc.js"],
            "imports": [r"describe\(", r"it\("],
            "config_keys": [],
        },
    }

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self._file_cache: Optional[List[Path]] = None
        self._content_cache: Dict[str, str] = {}

    def detect_patterns(self) -> List[str]:
        """
        Return list of detected patterns, e.g.:
        ['python-cli', 'pytest-tests', 'docker']
        """
        detected = []

        for pattern_name, pattern_def in self.PATTERNS.items():
            score = self._score_pattern(pattern_def)
            threshold = self.PATTERN_THRESHOLDS.get(pattern_name, 2)
            if score >= threshold:
                detected.append(pattern_name)

        return detected

    def detect_project_type(self) -> Dict:
        """
        Detect the primary project type with confidence.

        Returns:
            {
                'type': 'python-cli',
                'patterns': ['python-cli', 'pytest-tests'],
                'entry_points': ['main.py'],
                'confidence': 0.85,
            }
        """
        patterns = self.detect_patterns()
        test_framework = self.detect_test_framework()
        entry_points = self._find_entry_points()

        # Score each pattern
        scores = {}
        for pattern_name, pattern_def in self.PATTERNS.items():
            scores[pattern_name] = self._score_pattern(pattern_def)

        # Pick best match
        if scores:
            best = max(scores, key=lambda k: scores[k])
            max_score = scores[best]

            # If 'library' wins but a more specific application type has a
            # strong signal (>= 2, i.e. confirmed), prefer the application type.
            # 'library' is a generic fallback that matches packaging files
            # (setup.py, pyproject.toml) which most Python projects have.
            if best == "library":
                app_types = {
                    k: v for k, v in scores.items()
                    if k != "library" and v >= self.PATTERN_THRESHOLDS.get(k, 2)
                }
                if app_types:
                    best = max(app_types, key=lambda k: app_types[k])
                    max_score = scores[best]

            # Confidence based on score strength
            confidence = min(1.0, max_score / 6.0)
        else:
            best = "unknown"
            confidence = 0.0

        # Distinguish library from application
        is_library = self._is_library()

        if is_library and best not in ("library",):
            patterns.append("library")

        result = {
            "type": best,
            "patterns": patterns,
            "entry_points": entry_points,
            "confidence": round(confidence, 2),
            "is_library": is_library,
            "all_scores": scores,
        }

        if test_framework:
            result["test_framework"] = test_framework
            patterns.append(f"{test_framework}-tests")

        return result

    def _has_js_or_ts_files(self) -> bool:
        """Return True if the project contains any .js or .ts source files."""
        for ext in ("*.js", "*.ts", "*.jsx", "*.tsx"):
            if any(self.project_path.rglob(ext)):
                return True
        return (self.project_path / "package.json").exists()

    def detect_test_framework(self) -> Optional[str]:
        """Detect which test framework is in use."""
        for framework, definition in self.TEST_PATTERNS.items():
            # jest and mocha are JavaScript-only frameworks.  Checking their
            # import patterns against Python test files produces false positives
            # (e.g. `it(` matches inline comments or helper calls in .py files).
            # Guard: only consider JS/TS frameworks when the project actually has
            # JS or TS files (or a package.json).
            if framework in ("jest", "mocha") and not self._has_js_or_ts_files():
                continue

            # Check for config files
            for fname in definition.get("files", []):
                if (self.project_path / fname).exists():
                    return framework

            # Check imports in test files
            test_files = self._get_test_files()
            for tf in test_files[:10]:  # Limit scan
                content = self._read_file_cached(tf)
                for pattern in definition.get("imports", []):
                    if re.search(pattern, content):
                        return framework

            # Check pyproject.toml for config keys and dep name patterns
            pyproject = self.project_path / "pyproject.toml"
            if pyproject.exists():
                content = self._read_file_cached(pyproject)
                for key in definition.get("config_keys", []):
                    if key in content:
                        return framework
                for pattern in definition.get("dep_patterns", []):
                    if re.search(pattern, content, re.MULTILINE):
                        return framework

        return None

    def analyze_tests(self) -> Dict:
        """
        Analyze test patterns in the project.

        Returns:
            {
                'framework': 'pytest',
                'test_files': 15,
                'patterns': ['unit', 'integration'],
                'has_fixtures': True,
                'has_conftest': True,
            }
        """
        framework = self.detect_test_framework()
        test_files = self._get_test_files()
        test_dirs = self._get_test_dirs()

        patterns = []
        has_fixtures = False
        has_conftest = False

        for tf in test_files:
            name = tf.name.lower()
            if "integration" in name:
                if "integration" not in patterns:
                    patterns.append("integration")
            elif "e2e" in name or "end_to_end" in name:
                if "e2e" not in patterns:
                    patterns.append("e2e")
            else:
                if "unit" not in patterns:
                    patterns.append("unit")

        # Check for fixtures
        fixture_dirs = [d for d in test_dirs if "fixture" in d.name.lower()]
        has_fixtures = len(fixture_dirs) > 0
        has_conftest = (self.project_path / "tests" / "conftest.py").exists()

        # Count actual test functions/methods
        test_cases = self._count_test_cases(test_files)

        return {
            "framework": framework,
            "test_files": len(test_files),
            "test_cases": test_cases,
            "patterns": patterns,
            "has_fixtures": has_fixtures,
            "has_conftest": has_conftest,
        }

    def _count_test_cases(self, test_files: List[Path]) -> int:
        """Count test functions and methods across test files.

        Counts top-level ``def test_*`` functions and ``def test_*`` methods
        inside classes.  For JS/TS files it counts ``it(`` and ``test(`` calls.
        """
        count = 0
        py_pattern = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)\s*\(", re.MULTILINE)
        js_pattern = re.compile(r"^\s*(?:it|test)\s*\(", re.MULTILINE)

        for tf in test_files:
            try:
                if tf.stat().st_size > 1024 * 1024:  # skip files > 1 MB
                    continue
                content = tf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if tf.suffix == ".py":
                count += len(py_pattern.findall(content))
            elif tf.suffix in (".js", ".ts", ".jsx", ".tsx"):
                count += len(js_pattern.findall(content))
        return count

    def _score_pattern(self, pattern_def: Dict) -> int:
        """Score how well a pattern matches the project."""
        score = 0

        # Check folders
        for folder in pattern_def.get("folders", []):
            if (self.project_path / folder).is_dir():
                score += 2

        # Check specific files
        for fname in pattern_def.get("files", []):
            matches = list(self.project_path.rglob(fname))
            if matches:
                score += 1

        # Check imports in source files
        source_files = self._get_source_files()
        for sf in source_files[:30]:  # Limit to avoid perf issues
            content = self._read_file_cached(sf)
            for pattern in pattern_def.get("imports", []):
                if re.search(pattern, content):
                    score += 2
                    break  # One match per file is enough

        return score

    def _is_library(self) -> bool:
        """Detect if project is a library (vs application)."""
        has_setup = (self.project_path / "setup.py").exists()
        has_pyproject = (self.project_path / "pyproject.toml").exists()
        has_main = any(
            (self.project_path / f).exists() for f in ["main.py", "app.py", "run.py", "server.py", "manage.py"]
        )
        has_src_init = (self.project_path / "src" / "__init__.py").exists()

        # Library signals: has packaging files but no obvious main entry
        if (has_setup or has_pyproject) and not has_main and has_src_init:
            return True
        return False

    def _find_entry_points(self) -> List[str]:
        """Find likely entry point files."""
        candidates = [
            "main.py",
            "app.py",
            "run.py",
            "server.py",
            "manage.py",
            "cli.py",
            "__main__.py",
            "index.js",
            "index.ts",
            "server.js",
        ]
        found = []
        for c in candidates:
            matches = list(self.project_path.glob(c))
            matches.extend(self.project_path.glob(f"src/{c}"))
            for m in matches:
                found.append(str(m.relative_to(self.project_path)))
        return found

    def _get_source_files(self) -> List[Path]:
        """Get Python and JS/TS source files."""
        if self._file_cache is not None:
            return self._file_cache

        files = []
        extensions = {".py", ".js", ".ts", ".jsx", ".tsx"}
        for f in self.project_path.rglob("*"):
            if f.suffix in extensions and not self._should_skip(f):
                files.append(f)
                if len(files) >= 100:  # Safety limit
                    break

        self._file_cache = files
        return files

    def _get_test_files(self) -> List[Path]:
        """Find test files."""
        test_files = []
        for f in self.project_path.rglob("test_*.py"):
            if not self._should_skip(f):
                test_files.append(f)
        for f in self.project_path.rglob("*_test.py"):
            if not self._should_skip(f):
                test_files.append(f)
        # JS tests
        for pattern in ["*.test.js", "*.test.ts", "*.spec.js", "*.spec.ts"]:
            for f in self.project_path.rglob(pattern):
                if not self._should_skip(f):
                    test_files.append(f)
        return test_files

    def _get_test_dirs(self) -> List[Path]:
        """Find test-related directories."""
        test_dirs = []
        for d in self.project_path.rglob("*"):
            if d.is_dir() and not self._should_skip(d):
                if d.name in ("tests", "test", "__tests__", "fixtures", "test_data"):
                    test_dirs.append(d)
        return test_dirs

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        parts = path.parts
        for skip in SKIP_DIRS:
            if skip in parts:
                return True
        return False

    def _read_file_cached(self, path: Path) -> str:
        """Read file with caching."""
        key = str(path)
        if key not in self._content_cache:
            try:
                self._content_cache[key] = path.read_text(encoding="utf-8", errors="replace")[:5000]
            except OSError:
                self._content_cache[key] = ""
        return self._content_cache[key]
