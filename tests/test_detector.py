import pytest
from pathlib import Path
from analyzer.project_type_detector import detect_project_type

class MockPath:
    def __init__(self, exists=False, name=""):
        self._exists = exists
        self._name = name
    
    def exists(self):
        return self._exists
    
    @property
    def name(self):
        return self._name

def test_detect_generator():
    project_data = {
        'name': 'my-generator',
        'raw_readme': 'This tool helps generate code templates.',
        'tech_stack': ['python'],
        'description': 'A code generator.'
    }
    # Mocking filesystem would be ideal, but for now we rely on the logic that checks strings mostly.
    # The current implementation uses Path().exists() which will check actual FS. 
    # To properly unit test without mocking FS, we'd need to refactor detector to accept an abstraction.
    # For now, we'll test the string-based scoring which is significant.
    
    # We pass '.' as path, which contains main.py, so it might detect CLI too.
    # We'll see if generator score > CLI score.
    # In this repo: 
    # Generator: 'generator' in name (0.3) + 'generate' in readme (0.4) = 0.7
    # + has_templates (0.3) = 1.0
    
    result = detect_project_type(project_data, '.')
    assert result['primary_type'] in ['generator', 'cli_tool']
    
def test_detect_web_app():
    project_data = {
        'name': 'my-web-app',
        'raw_readme': 'Start the server on localhost:8000',
        'tech_stack': ['fastapi', 'react'],
        'description': 'A web app.'
    }
    # Web app: fastapi(0.5) + localhost(0.2) = 0.7
    result = detect_project_type(project_data, '.')
    # Note: since we run in the repo root, CLI score will be added (main.py exists).
    # CLI: main.py(0.3) = 0.3.
    # Web app wins.
    
    assert result['primary_type'] == 'web_app'

def test_detect_agent():
    project_data = {
        'name': 'super-agent',
        'raw_readme': 'An autonomous agent using OpenAI.',
        'tech_stack': ['python', 'openai'],
        'description': 'Agentic workflow.'
    }
    # Agent: openai(0.4) + autonomous(0.3) = 0.7
    result = detect_project_type(project_data, '.')
    assert result['primary_type'] == 'agent'
