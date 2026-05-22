"""Pytest-driven tests. Bug4: detector wrongly inferred 'jest' from skill names
in the global learned cache rather than from this project's actual test files."""

import pytest

from workflow.agent import build_workflow


@pytest.mark.asyncio
async def test_workflow_compiles():
    assert build_workflow() is not None
