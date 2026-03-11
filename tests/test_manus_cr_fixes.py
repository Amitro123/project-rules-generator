"""
Regression tests for the 5 issues identified in manus_CR.md.

Fix 1 & 2: pyproject.toml — tested indirectly (package import smoke test)
Fix 3: extract_process_steps — broader section headers + bullet lists
Fix 4: extract_anti_patterns — Coding Standards / negative imperatives
Fix 5: skill_discovery — uses logging, not print, for warnings
"""

import ast
import importlib
import re
from pathlib import Path

import pytest

from generator.analyzers.readme_parser import extract_anti_patterns, extract_process_steps

# ---------------------------------------------------------------------------
# Fix 3: extract_process_steps
# ---------------------------------------------------------------------------

CALCULATOR_README = """
# Super Calculator

A simple calculator project.

## Features
- Addition
- Subtraction

## Development Workflow
To add a new operation:
1. Create a new file in `ops/`
2. Implement the `calculate` function
3. Add tests in `tests/`
4. Run `pytest` to verify

## Coding Standards
- Always use type hints
- Never use global variables
- Use `decimal` for financial calculations
"""


class TestExtractProcessStepsGeneralized:
    """Fix 3: process steps should be extracted from workflow sections."""

    def test_numbered_steps_from_development_workflow(self):
        """Numbered list items under '## Development Workflow' must be captured."""
        steps = extract_process_steps(CALCULATOR_README)
        texts = " ".join(steps)
        assert "Create a new file" in texts, (
            f"Step 1 ('Create a new file') not extracted.\nGot: {steps}"
        )
        assert "calculate" in texts, (
            f"Step 2 ('calculate') not extracted.\nGot: {steps}"
        )

    def test_multiple_steps_returned(self):
        """All 4 numbered steps from the workflow section should be captured."""
        steps = extract_process_steps(CALCULATOR_README)
        # Filter to items that look like numbered steps (not code blocks)
        numbered = [s for s in steps if re.match(r"^\d+[\.)]\s+", s)]
        assert len(numbered) >= 4, (
            f"Expected ≥4 numbered steps, got {len(numbered)}.\nSteps: {steps}"
        )

    def test_bullet_list_steps_extracted(self):
        """Bullet-list workflow steps should also be captured."""
        readme = """
# My Project

## Workflow
- Step A: clone the repo
- Step B: install deps
- Step C: run tests
"""
        steps = extract_process_steps(readme)
        texts = " ".join(steps)
        assert "clone the repo" in texts, f"Bullet step A not found.\nGot: {steps}"
        assert "install deps" in texts, f"Bullet step B not found.\nGot: {steps}"

    def test_installation_section_still_works(self):
        """Original behaviour: still captures numbered steps under Installation."""
        readme = """
# Project

## Installation
1. Clone repo
2. pip install -e .
3. Verify with prg --version
"""
        steps = extract_process_steps(readme)
        texts = " ".join(steps)
        assert "Clone repo" in texts
        assert "pip install" in texts

    def test_no_steps_returns_empty_list(self):
        """README with no workflow/install sections returns []."""
        readme = "# Project\n\nJust a description with no steps.\n"
        steps = extract_process_steps(readme)
        assert steps == []

    def test_max_steps_capped_at_ten(self):
        """Even if many steps exist, at most 10 are returned."""
        items = "\n".join([f"{i}. Step {i}" for i in range(1, 20)])
        readme = f"# Project\n\n## Installation\n{items}\n"
        steps = extract_process_steps(readme)
        assert len(steps) <= 10


# ---------------------------------------------------------------------------
# Fix 4: extract_anti_patterns — Coding Standards sections
# ---------------------------------------------------------------------------


class TestExtractAntiPatternsFromCodingStandards:
    """Fix 4: negative imperatives in 'Coding Standards' sections are captured."""

    def test_never_statement_extracted(self):
        """'Never use global variables' → anti-pattern."""
        patterns = extract_anti_patterns(CALCULATOR_README, tech=[])
        texts = " ".join(patterns)
        assert "global variables" in texts, (
            f"'Never use global variables' not found in anti-patterns.\nGot: {patterns}"
        )

    def test_positive_rule_not_extracted(self):
        """'Always use type hints' MUST NOT appear as an anti-pattern."""
        patterns = extract_anti_patterns(CALCULATOR_README, tech=[])
        texts = " ".join(patterns)
        assert "type hints" not in texts, (
            f"Positive rule 'type hints' incorrectly included as anti-pattern.\nGot: {patterns}"
        )

    def test_do_not_statement_extracted(self):
        """'Do not import * from modules' → anti-pattern."""
        readme = """
# Project

## Best Practices
- Do not import * from modules
- Always write tests
- Never commit secrets to git
"""
        patterns = extract_anti_patterns(readme, tech=[])
        texts = " ".join(patterns)
        assert "import" in texts.lower(), (
            f"'Do not import *' not captured.\nGot: {patterns}"
        )
        assert "secrets" in texts.lower(), (
            f"'Never commit secrets' not captured.\nGot: {patterns}"
        )

    def test_dont_statement_extracted(self):
        """Contraction form "Don't use X" is also captured."""
        readme = """
# Project

## Coding Standards
- Don't use mutable default arguments
"""
        patterns = extract_anti_patterns(readme, tech=[])
        texts = " ".join(patterns)
        assert "mutable default" in texts, (
            f"Don't-form not captured.\nGot: {patterns}"
        )

    def test_avoid_statement_extracted(self):
        """'Avoid using bare except clauses' → anti-pattern."""
        readme = """
# Project

## Guidelines
- Avoid using bare except clauses
- Use structured logging
"""
        patterns = extract_anti_patterns(readme, tech=[])
        texts = " ".join(patterns)
        assert "bare except" in texts, (
            f"Avoid-form not captured.\nGot: {patterns}"
        )

    def test_existing_cross_mark_not_duplicated(self):
        """Items already captured via ❌ are not duplicated by the standards pass."""
        readme = """
# Project

❌ Never leak credentials

## Coding Standards
- Never leak credentials
"""
        patterns = extract_anti_patterns(readme, tech=[])
        credential_hits = [p for p in patterns if "credential" in p.lower()]
        assert len(credential_hits) == 1, (
            f"Expected 1 credential anti-pattern, got {len(credential_hits)}.\nPatterns: {patterns}"
        )

    def test_best_practices_section_recognised(self):
        """'Best Practices' header is recognised as a standards section."""
        readme = """
# Project

## Best Practices
- Avoid hardcoding paths
- Use environment variables
"""
        patterns = extract_anti_patterns(readme, tech=[])
        texts = " ".join(patterns)
        assert "hardcoding paths" in texts


# ---------------------------------------------------------------------------
# Fix 5: skill_discovery uses logging, not print
# ---------------------------------------------------------------------------


class TestSkillDiscoveryUsesLogging:
    """Fix 5: all [Warning] messages must use logging, not print."""

    def test_no_print_for_warnings_in_source(self):
        """The skill_discovery.py source file must not contain print([Warning] calls."""
        source_path = Path(__file__).parent.parent / "generator" / "skill_discovery.py"
        assert source_path.exists(), f"Source file not found: {source_path}"
        source = source_path.read_text(encoding="utf-8")
        # Look for print calls that contain "[Warning]" text
        bad_prints = [
            line.strip()
            for line in source.splitlines()
            if re.search(r'print\s*\(', line) and "Warning" in line
        ]
        assert not bad_prints, (
            f"Found print-based warnings in skill_discovery.py:\n" + "\n".join(bad_prints)
        )

    def test_logging_imported_in_skill_discovery(self):
        """skill_discovery.py must import logging."""
        source_path = Path(__file__).parent.parent / "generator" / "skill_discovery.py"
        source = source_path.read_text(encoding="utf-8")
        assert "import logging" in source, "logging not imported in skill_discovery.py"

    def test_logger_getlogger_used(self):
        """A module-level logger must be created via logging.getLogger."""
        source_path = Path(__file__).parent.parent / "generator" / "skill_discovery.py"
        source = source_path.read_text(encoding="utf-8")
        assert "logging.getLogger" in source, "logging.getLogger not found in skill_discovery.py"
