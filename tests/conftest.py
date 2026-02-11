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


@pytest.fixture
def mock_ai_client(monkeypatch):
    """Mock AI client for testing."""
    class MockClient:
        def generate(self, prompt, max_tokens=2000, model=None):
            return "Mock AI Response"
            
    def mock_factory(provider='groq', **kwargs):
        return MockClient()
        
    monkeypatch.setattr("generator.ai.ai_client.create_ai_client", mock_factory)
    monkeypatch.setattr("generator.llm_skill_generator.create_ai_client", mock_factory)
    monkeypatch.setattr("generator.design_generator.create_ai_client", mock_factory)
    return MockClient()
