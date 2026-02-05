"""Pytest configuration and fixtures."""
import pytest
from pathlib import Path


@pytest.fixture
def sample_project_path():
    """Return path to sample project for testing."""
    return Path(__file__).parent / 'test_samples' / 'sample-project'


@pytest.fixture
def sample_readme_content():
    """Return sample README content for testing."""
    return """# Test Project

A sample project for testing the generator.

## Features

✅ Fast processing
✅ Multiple output formats
✅ Easy configuration

## Tech Stack

- Python 3.11
- FastAPI for API
- Docker for deployment

## License

MIT
"""


@pytest.fixture
def mock_config():
    """Return mock configuration for testing."""
    return {
        'llm': {'enabled': False},
        'git': {
            'auto_commit': True,
            'commit_message': 'Test commit',
            'commit_user_name': 'Test',
            'commit_user_email': 'test@test.com'
        },
        'generation': {
            'verbose': False,
            'max_description_length': 200
        }
    }
