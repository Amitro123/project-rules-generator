import logging

import pytest
from pydantic import ValidationError

from generator.pack_manager import load_external_packs
from prg_utils.config_schema import RootConfig, validate_config


def test_llm_config_accepts_all_providers():
    """LLMConfig must accept all four advertised providers (Issue #30: openai was missing)."""
    from prg_utils.config_schema import LLMConfig

    for provider in ("anthropic", "gemini", "groq", "openai"):
        cfg = LLMConfig(provider=provider)
        assert cfg.provider == provider, f"LLMConfig rejected provider={provider!r}"


def test_validate_config_openai_provider():
    """validate_config must not raise when provider='openai' (Issue #30 regression guard)."""
    config = {"llm": {"provider": "openai", "enabled": True}}
    validated = validate_config(config)
    assert validated.llm.provider == "openai"


def test_validate_config_valid():
    config = {
        "llm": {"enabled": True},
        "git": {"auto_commit": False},
        "generation": {"max_feature_count": 10},
    }
    validated = validate_config(config)
    assert isinstance(validated, RootConfig)
    assert validated.llm.enabled is True
    assert validated.git.auto_commit is False
    assert validated.generation.max_feature_count == 10


def test_validate_config_invalid():
    config = {"generation": {"max_feature_count": 100}}  # Too high, max 20
    with pytest.raises(ValidationError):
        validate_config(config)


def test_logger_setup(caplog):
    from prg_utils.logger import setup_logging

    setup_logging(verbose=True)
    logger = logging.getLogger("project_rules_generator")

    logger.debug("Test debug message")
    logger.info("Test info message")

    # Check if messages are captured (caplog uses root logger by default, but we configured 'project_rules_generator')
    # setup_logging configures 'project_rules_generator'.
    # caplog captures the root logger by default.
    # However, 'project_rules_generator' propagates to root unless disabled.
    # But wait, our setup_configure creates a handler on 'project_rules_generator' logger, not root?
    # "root = logging.getLogger('project_rules_generator')" <- naming variable 'root' is confusing but keys on name.

    # Let's verify that log messages are emitted to stdout/stderr or captured by caplog if we use the specific logger.

    assert "Test info message" in [r.message for r in caplog.records]


def test_pack_manager_logging(caplog):
    # This tests that pack manager uses the logger we expect
    with caplog.at_level(logging.INFO, logger="generator.pack_manager"):
        load_external_packs(
            [], verbose=True
        )  # Verbose flag is now ignored/redundant for logging config inside, but used in logic?
        # Actually load_external_packs calls logger.info("Loading external packs...") if verbose is NOT checked?
        # Let's check the code.
        # It logs "Loading external packs..." unconditionally now?
        # Previous code: if verbose: click.echo...
        # New code: logger.info("Loading external packs...")

        pass

    # Wait, if I call it with empty list, it returns immediately.
    # "if not packs_to_load: return external_packs"
    # So it won't log anything.

    # Let's try with a dummy pack name
    with caplog.at_level(logging.INFO):
        load_external_packs(["dummy-pack"])

    assert "Loading external packs..." in [r.message for r in caplog.records]
    assert "Pack not found: dummy-pack" in [r.message for r in caplog.records]
