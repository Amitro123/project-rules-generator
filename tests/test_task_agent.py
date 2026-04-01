"""Tests for TaskImplementationAgent._sanitize_path and _parse_response."""

import pytest

from generator.exceptions import SecurityError
from generator.planning.task_agent import TaskImplementationAgent


@pytest.fixture
def agent():
    # Bypass real AI client construction
    a = object.__new__(TaskImplementationAgent)
    a.client = None
    return a


# ── _sanitize_path ─────────────────────────────────────────────────────────


def test_sanitize_valid_relative(agent):
    assert agent._sanitize_path("src/main.py") == "src/main.py"


def test_sanitize_normalises_backslash(agent):
    # Windows-style separators from LLM output should be normalised
    result = agent._sanitize_path("src\\utils\\helper.py")
    assert result == "src/utils/helper.py"


def test_sanitize_rejects_absolute_unix(agent):
    assert agent._sanitize_path("/etc/passwd") is None


def test_sanitize_rejects_absolute_windows(agent):
    assert agent._sanitize_path("C:\\Windows\\system32\\evil.dll") is None


def test_sanitize_rejects_traversal(agent):
    assert agent._sanitize_path("../../etc/shadow") is None


def test_sanitize_rejects_traversal_nested(agent):
    assert agent._sanitize_path("src/../../../etc/passwd") is None


def test_sanitize_rejects_empty(agent):
    assert agent._sanitize_path("   ") is None


# ── _parse_response ────────────────────────────────────────────────────────


def test_parse_response_valid(agent):
    response = "[FILE: src/foo.py]\nprint('hello')\n[FILE: tests/test_foo.py]\nassert True"
    result = agent._parse_response(response)
    assert result == {
        "src/foo.py": "print('hello')",
        "tests/test_foo.py": "assert True",
    }


def test_parse_response_raises_on_traversal(agent):
    response = "[FILE: ../../etc/passwd]\nmalicious content"
    with pytest.raises(SecurityError):
        agent._parse_response(response)


def test_parse_response_raises_on_absolute(agent):
    response = "[FILE: /etc/crontab]\n* * * * * evil"
    with pytest.raises(SecurityError):
        agent._parse_response(response)


def test_parse_response_empty_response(agent):
    assert agent._parse_response("") == {}


def test_parse_response_no_file_markers(agent):
    assert agent._parse_response("Just some text without markers") == {}
