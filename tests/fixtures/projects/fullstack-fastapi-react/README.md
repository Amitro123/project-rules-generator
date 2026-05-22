# Fullstack FastAPI + React

A canonical fullstack app: Python FastAPI backend in `backend/`, React +
TypeScript frontend in `frontend/`. Both halves are first-class.

## Bug context

Claude review1#5 in `ListOfBugs/`: the enhanced parser correctly detects
`web-app` with 1.0 confidence, but the frontmatter in `rules.md` still
wrote `project_type: python-cli` because `project_data` was populated
before the reconciler ran. The two snapshots disagreed.

## Stack

- **Backend**: FastAPI, Pydantic, Uvicorn
- **Frontend**: React 18, TypeScript, Vite
- **Tests**: pytest (backend), Vitest (frontend, not included in fixture)
