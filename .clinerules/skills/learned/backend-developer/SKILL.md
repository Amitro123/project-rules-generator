---
name: backend-developer
description: Automates setup and testing of a backend project using Python.
auto_triggers:
  - keywords: [backend, python, api]
    project_signals: [has_python, has_api]
tools: [pip, poetry, pytest]
---

# Skill: Backend Developer

## Purpose
This skill automates the setup and testing of a backend project using Python, ensuring that the project is properly configured and tested.

## Process

### 1. Install Dependencies
```bash
# Install dependencies using Poetry
poetry install
```

### 2. Run Tests
```bash
# Run tests using pytest
pytest tests/
```

### 3. Generate API Documentation
```bash
# Generate API documentation using Swagger
swagger generate spec -i api/openapi.yaml -o api/docs/
```

### 4. Build Docker Image
```bash
# Build Docker image using Docker
docker build -t backend-api .
```

### 5. Deploy to Production
```bash
# Deploy to production using Docker Compose
docker-compose up -d
```

## Output
- `api/docs/index.html`: API documentation
- `api/openapi.yaml`: OpenAPI specification
- `tests/test_api.py`: Test results

## Anti-Patterns
❌ **Not using a virtual environment**: → Create a new virtual environment using `python -m venv venv` and activate it.
❌ **Not committing dependencies**: → Use `poetry install` to ensure dependencies are committed to the repository.

## Tech Stack Notes
This skill assumes the project uses Python 3.x and has the following structure:

```bash
project/
api/
openapi.yaml
main.py
requirements.txt
tests/
test_api.py
__init__.py
Dockerfile
docker-compose.yml
```

The skill uses Poetry for dependency management and pytest for testing. Docker and Docker Compose are used for building and deploying the API.