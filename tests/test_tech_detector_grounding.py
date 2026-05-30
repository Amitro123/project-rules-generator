"""Grounding tests for tech detection (task #12).

Regression target: ``gravity-claw-hub`` — a Vite + React + TypeScript + Vitest +
Tailwind + shadcn/ui + TanStack Query + React Router frontend. Before grounding,
``tech_detector`` (the shared producer behind ``create-rules`` and the skills
scanner):

* missed vite / vitest / tailwind / tanstack-query / react-router entirely, because
  ``detect_from_dependencies`` used a hardcoded 10-entry ``node_map`` with no
  knowledge of the modern Vite ecosystem;
* false-detected ``jest`` from the ``@testing-library/jest-dom`` devDependency
  (substring matching), even though the project runs Vitest;
* leaked ``telegram`` — a notification *channel* named once in the README — into
  the build ``tech_stack``.

These tests pin the grounded behavior: detection comes from real ``package.json``
dependency *keys* and config-file presence; communication channels are not promoted
from README prose when a real build stack is present; and the test runner is
disambiguated (Vitest, never Jest, on a Vitest project).
"""

from __future__ import annotations

import json
from pathlib import Path

from generator.utils.tech_detector import detect_from_dependencies, detect_tech_stack

# Mirrors gravity-claw-hub/package.json, trimmed to the signal-bearing deps.
_PACKAGE_JSON: dict = {
    "name": "vite_react_shadcn_ts",
    "private": True,
    "type": "module",
    "scripts": {
        "dev": "vite",
        "build": "vite build",
        "test": "vitest run",
        "test:watch": "vitest",
    },
    "dependencies": {
        "@radix-ui/react-dialog": "^1.1.14",
        "@tanstack/react-query": "^5.83.0",
        "react": "^18.3.1",
        "react-dom": "^18.3.1",
        "react-router-dom": "^6.30.1",
        "tailwind-merge": "^2.6.0",
        "zod": "^3.25.76",
    },
    "devDependencies": {
        "@testing-library/jest-dom": "^6.6.0",
        "@testing-library/react": "^16.0.0",
        "@types/react": "^18.3.23",
        "@vitejs/plugin-react-swc": "^3.11.0",
        "tailwindcss": "^3.4.17",
        "typescript": "^5.8.3",
        "vite": "^5.4.19",
        "vitest": "^3.2.4",
    },
}

_CONFIG_FILES = ("vite.config.ts", "vitest.config.ts", "tailwind.config.ts", "components.json")


def _make_project(tmp_path: Path, *, with_configs: bool = True, readme: str | None = None) -> Path:
    (tmp_path / "package.json").write_text(json.dumps(_PACKAGE_JSON), encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "App.tsx").write_text("export const App = () => null;\n", encoding="utf-8")
    if with_configs:
        for name in _CONFIG_FILES:
            (tmp_path / name).write_text("// config\n", encoding="utf-8")
    if readme is not None:
        (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    return tmp_path


def test_modern_vite_stack_detected_from_manifest(tmp_path):
    """Every modern dep in package.json must be detected from its exact key."""
    project = _make_project(tmp_path, with_configs=False)

    detected = detect_from_dependencies(project)

    assert {"react", "vite", "vitest", "tailwindcss", "tanstack-query", "react-router"} <= detected
    assert "typescript" in detected
    assert "javascript" not in detected  # typescript present -> not a plain-JS project


def test_jest_dom_devdep_does_not_trigger_jest(tmp_path):
    """`@testing-library/jest-dom` must not be misread as the Jest test runner."""
    project = _make_project(tmp_path, with_configs=False)

    detected = detect_from_dependencies(project)

    assert "jest" not in detected


def test_vitest_is_the_only_test_runner(tmp_path):
    """Full detection on a Vitest project yields vitest and never jest."""
    project = _make_project(tmp_path)

    detected = set(detect_tech_stack(project, ""))

    assert "vitest" in detected
    assert "jest" not in detected


def test_config_file_presence_grounds_detection(tmp_path):
    """vite/vitest/tailwind/shadcn are detected from root config files alone."""
    project = _make_project(tmp_path)

    detected = set(detect_tech_stack(project, ""))

    assert {"vite", "vitest", "tailwindcss", "shadcn"} <= detected


def test_telegram_channel_not_promoted_when_real_stack_present(tmp_path):
    """A prose mention of a notification channel must not leak into the stack."""
    readme = "# Gravity Claw Hub\n\n" "A Vite + React dashboard. Cost alerts are delivered via Telegram and WhatsApp.\n"
    project = _make_project(tmp_path, readme=readme)

    detected = set(detect_tech_stack(project, readme))

    assert "telegram" not in detected
    assert "whatsapp" not in detected
    # ...but the real build stack is still there:
    assert {"react", "vite", "tailwindcss"} <= detected


def test_nextjs_not_detected_without_dep_or_config(tmp_path):
    """A README that merely name-drops Next.js must not add nextjs to the stack."""
    project = _make_project(tmp_path)

    detected = set(detect_tech_stack(project, "Routing patterns inspired by Next.js."))

    assert "nextjs" not in detected


def test_telegram_still_detected_for_docsonly_ops_repo(tmp_path):
    """Guard against over-correction: a deps-free ops repo whose README *is* the
    manifest must still surface its operational channels and infra.

    Mirrors the existing agent-skills-repo regression: when there are no Python or
    Node dependency files at all, README prose is the primary (only) source.
    """
    readme = "# Ops Bot\n\nDeployed with Docker. Sends alerts to a Telegram channel.\n"
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")

    detected = set(detect_tech_stack(tmp_path, readme))

    assert "telegram" in detected
    assert "docker" in detected
