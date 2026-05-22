"""Tests for the declarative tech-detection rule loader (Phase 3b).

The loader reads YAML files under ``generator/rules/tech-detection/`` and
turns them into ``PrecedenceRule`` / ``TechCleanupRule`` tuples that the
generic functions in ``generator.project_profile`` consume.

These tests pin:
  * The shipped YAML rule files load successfully and produce the same
    rules the Phase 2 / 3a Python tuples did.
  * Behavior parity: every assertion the previous tests made about
    DEFAULT_PROJECT_TYPE_PRECEDENCE / DEFAULT_TECH_CLEANUP_RULES still
    holds after the YAML migration.
  * Robustness: missing dirs, empty files, malformed predicates, unknown
    predicate types all surface as warnings, never crashes.
  * Genericity: loading custom YAML files from arbitrary paths produces
    custom rule tables — confirms the loader has no hardcoded knowledge
    of the shipped rule files.

After this phase, **adding a new tech-detection rule is a YAML PR with
zero Python edits**. These tests are the contract that enforces it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from generator.rules.tech_detection_loader import (
    CLEANUP_DIR_NAME,
    CLEANUP_PREDICATE_BUILDERS,
    PRECEDENCE_DIR_NAME,
    PRECEDENCE_PREDICATE_BUILDERS,
    RuleParseError,
    load_cleanup_rules,
    load_precedence_rules,
)

# --- The shipped rule files load successfully ------------------------------


def test_shipped_precedence_rules_load_in_correct_count_and_order():
    """The 5 YAML files under project-type-precedence/ produce 5 rules in
    lexicographic filename order. If a future contributor adds/removes a
    rule, the count assertion will need updating — and reviewers will see
    a deliberate edit, not silent drift."""
    rules = load_precedence_rules()
    names = [r.name for r in rules]
    assert names == [
        "python-api-always-wins",
        "agent-skills-high-confidence",
        "agent-when-structure-unsure",
        "generator-or-webapp-on-fallback",
        "any-newer-on-fallback",
    ]


def test_shipped_cleanup_rules_load_in_correct_count_and_order():
    rules = load_cleanup_rules()
    names = [r.name for r in rules]
    assert names == [
        "strip-gpt-vague-token",
        "strip-jest-when-not-test-framework",
        "strip-reflex-js-build-artifacts",
    ]


def test_loaded_rules_have_reasons():
    """Every loaded rule has a non-empty reason string. The reason is what
    shadow logs / debug output show; an empty reason is useless."""
    for rule in load_precedence_rules() + tuple():
        assert rule.reason, f"Precedence rule {rule.name!r} has empty reason"
    for rule in load_cleanup_rules() + tuple():
        assert rule.reason, f"Cleanup rule {rule.name!r} has empty reason"


# --- Behaviour parity with the previous hardcoded tuples -------------------


def test_loaded_precedence_python_api_always_wins():
    """Behaviour parity: python-api wins regardless of structure confidence."""
    from generator.project_profile import reconcile_project_type

    r = reconcile_project_type(
        structure_type="python-cli",
        structure_confidence=1.0,
        newer_type="python-api",
        newer_confidence=0.1,
    )
    assert r.project_type == "python-api"
    assert r.rule_fired == "python-api-always-wins"


def test_loaded_precedence_agent_skills_threshold():
    from generator.project_profile import reconcile_project_type

    # Above threshold — fires
    r = reconcile_project_type(
        structure_type="python-cli",
        structure_confidence=0.95,
        newer_type="agent-skills",
        newer_confidence=0.85,
    )
    assert r.project_type == "agent-skills"
    # Below threshold — doesn't fire
    r2 = reconcile_project_type(
        structure_type="python-cli",
        structure_confidence=0.95,
        newer_type="agent-skills",
        newer_confidence=0.7,
    )
    assert r2.project_type == "python-cli"


def test_loaded_cleanup_strips_gpt_always():
    """Behaviour parity: gpt is stripped on every run."""
    from generator.project_profile import apply_tech_cleanup_rules

    cleaned, traces = apply_tech_cleanup_rules(
        tech_stack=frozenset({"gpt", "python"}),
        context={},
    )
    assert "gpt" not in cleaned
    assert any(t.rule_name == "strip-gpt-vague-token" for t in traces)


def test_loaded_cleanup_strips_reflex_js_artifacts():
    from generator.project_profile import apply_tech_cleanup_rules

    cleaned, _ = apply_tech_cleanup_rules(
        tech_stack=frozenset({"reflex", "python", "react", "node", "typescript", "nextjs"}),
        context={},
    )
    for stripped in ("react", "node", "typescript", "nextjs"):
        assert stripped not in cleaned
    assert "reflex" in cleaned
    assert "python" in cleaned


def test_loaded_cleanup_preserves_jest_when_test_framework_is_jest():
    from generator.project_profile import apply_tech_cleanup_rules

    cleaned, _ = apply_tech_cleanup_rules(
        tech_stack=frozenset({"react", "jest"}),
        context={"test_framework": "jest"},
    )
    assert "jest" in cleaned


# --- Loader robustness: never raises on bad input -------------------------


def test_load_precedence_from_missing_dir_returns_empty(tmp_path: Path):
    """Pointing the loader at a non-existent directory returns ()."""
    rules = load_precedence_rules(tmp_path / "does-not-exist")
    assert rules == ()


def test_load_cleanup_from_empty_dir_returns_empty(tmp_path: Path):
    (tmp_path / CLEANUP_DIR_NAME).mkdir()
    assert load_cleanup_rules(tmp_path) == ()


def test_load_skips_underscore_prefixed_files(tmp_path: Path):
    """Files starting with `_` are reserved for schema docs etc. and must
    not be parsed as rule files."""
    cleanup_dir = tmp_path / CLEANUP_DIR_NAME
    cleanup_dir.mkdir()
    # Underscore file with malformed content — would crash if parsed
    (cleanup_dir / "_schema.yaml").write_text("not: a: valid: rule", encoding="utf-8")
    # Should still load zero rules without raising
    assert load_cleanup_rules(tmp_path) == ()


def test_load_logs_and_skips_malformed_yaml(tmp_path: Path, caplog):
    """A YAML syntax error → file is logged and skipped, others continue."""
    import logging

    precedence_dir = tmp_path / PRECEDENCE_DIR_NAME
    precedence_dir.mkdir()
    (precedence_dir / "broken.yaml").write_text("name: broken\nmatch_newer: [unclosed", encoding="utf-8")
    # A second, valid file alongside
    (precedence_dir / "good.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "valid-rule",
                "match_newer": "python-api",
                "predicate": {"type": "always"},
                "reason": "test",
            }
        ),
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING, logger="generator.rules.tech_detection_loader"):
        rules = load_precedence_rules(tmp_path)

    # Only the valid file produced a rule
    assert len(rules) == 1
    assert rules[0].name == "valid-rule"
    # The broken file was logged
    assert any("broken" in rec.message.lower() for rec in caplog.records)


def test_load_logs_and_skips_missing_required_field(tmp_path: Path):
    """A rule file missing 'reason' is logged and skipped, other rules
    in the directory still load."""
    precedence_dir = tmp_path / PRECEDENCE_DIR_NAME
    precedence_dir.mkdir()
    # Missing 'reason'
    (precedence_dir / "01-bad.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "missing-reason",
                "match_newer": "python-api",
                "predicate": {"type": "always"},
            }
        ),
        encoding="utf-8",
    )
    # Valid alongside
    (precedence_dir / "02-good.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "ok",
                "match_newer": "python-api",
                "predicate": {"type": "always"},
                "reason": "ok",
            }
        ),
        encoding="utf-8",
    )
    rules = load_precedence_rules(tmp_path)
    assert [r.name for r in rules] == ["ok"]


def test_load_logs_and_skips_unknown_predicate_type(tmp_path: Path):
    """A predicate type the loader doesn't recognise is logged and the
    rule is skipped — other rules still load."""
    cleanup_dir = tmp_path / CLEANUP_DIR_NAME
    cleanup_dir.mkdir()
    (cleanup_dir / "bad.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "future-predicate",
                "predicate": {"type": "predicate-not-yet-implemented"},
                "strip": ["foo"],
                "reason": "test",
            }
        ),
        encoding="utf-8",
    )
    rules = load_cleanup_rules(tmp_path)
    assert rules == ()


# --- match_newer accepts string, list, or "*" sentinel ---------------------


def test_match_newer_accepts_list(tmp_path: Path):
    precedence_dir = tmp_path / PRECEDENCE_DIR_NAME
    precedence_dir.mkdir()
    (precedence_dir / "rule.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "list-match",
                "match_newer": ["generator", "web-app"],
                "predicate": {"type": "always"},
                "reason": "list",
            }
        ),
        encoding="utf-8",
    )
    rules = load_precedence_rules(tmp_path)
    assert len(rules) == 1
    assert rules[0].match_newer == frozenset({"generator", "web-app"})


def test_match_newer_accepts_star(tmp_path: Path):
    """The literal '*' string is the NEWER_TYPE_ANY sentinel."""
    from generator.project_profile import NEWER_TYPE_ANY

    precedence_dir = tmp_path / PRECEDENCE_DIR_NAME
    precedence_dir.mkdir()
    (precedence_dir / "rule.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "star-match",
                "match_newer": "*",
                "predicate": {"type": "always"},
                "reason": "wildcard",
            }
        ),
        encoding="utf-8",
    )
    rules = load_precedence_rules(tmp_path)
    assert rules[0].match_newer == NEWER_TYPE_ANY


def test_match_newer_rejects_non_string_non_list(tmp_path: Path):
    """A `match_newer: 12345` integer is invalid and the rule is dropped."""
    precedence_dir = tmp_path / PRECEDENCE_DIR_NAME
    precedence_dir.mkdir()
    (precedence_dir / "rule.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "weird",
                "match_newer": 42,
                "predicate": {"type": "always"},
                "reason": "test",
            }
        ),
        encoding="utf-8",
    )
    assert load_precedence_rules(tmp_path) == ()


# --- Genericity: any YAML file under the right shape works ---------------


def test_custom_rule_file_in_custom_root(tmp_path: Path):
    """The loader accepts an arbitrary root path — proves it has no
    hardcoded knowledge of the shipped tech-detection directory."""
    cleanup_dir = tmp_path / CLEANUP_DIR_NAME
    cleanup_dir.mkdir()
    (cleanup_dir / "01-custom-experiment.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "experimental-strip-policy",
                "predicate": {"type": "always"},
                "strip": ["whatever", "test-only"],
                "reason": "Custom experiment, not part of shipped rules.",
            }
        ),
        encoding="utf-8",
    )

    rules = load_cleanup_rules(tmp_path)
    assert len(rules) == 1
    assert rules[0].name == "experimental-strip-policy"
    assert rules[0].strip == frozenset({"whatever", "test-only"})


# --- Predicate builder registry is the single source of truth -------------


@pytest.mark.parametrize("ptype", list(PRECEDENCE_PREDICATE_BUILDERS.keys()))
def test_every_registered_precedence_predicate_builds(ptype, tmp_path):
    """Each entry in PRECEDENCE_PREDICATE_BUILDERS must be callable with
    plausible params and return a predicate. Catches a registry entry
    whose builder is broken."""
    # Provide a permissive params dict that satisfies any builder
    params = {
        "type": ptype,
        "threshold": 0.5,
        "newer_min": 0.5,
        "structure_max": 0.5,
        "fallback_structure_types": ["library", "unknown"],
    }
    builder = PRECEDENCE_PREDICATE_BUILDERS[ptype]
    predicate = builder(params)
    assert callable(predicate)
    # Sanity: predicates take 4 args
    result = predicate("python-cli", 0.5, "python-api", 0.5)
    assert isinstance(result, bool)


@pytest.mark.parametrize("ptype", list(CLEANUP_PREDICATE_BUILDERS.keys()))
def test_every_registered_cleanup_predicate_builds(ptype, tmp_path):
    """Same check for the cleanup-side builders."""
    params = {
        "type": ptype,
        "token": "some-token",
        "key": "some-key",
        "value": "some-value",
    }
    builder = CLEANUP_PREDICATE_BUILDERS[ptype]
    predicate = builder(params)
    assert callable(predicate)
    result = predicate(frozenset({"some-token"}), {"some-key": "different"})
    assert isinstance(result, bool)


# --- RuleParseError is well-formed -----------------------------------------


def test_rule_parse_error_is_value_error():
    """RuleParseError is a ValueError subclass, so callers expecting
    ValueError catch it naturally."""
    assert issubclass(RuleParseError, ValueError)
