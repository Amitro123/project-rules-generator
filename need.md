Add two-stage planning workflow (inspired by GitHub Spec-Kit):

STAGE 1: Technical Design (NEW)
Create prg design command:
```bash
prg design "Add authentication to API" --output DESIGN.md
Output (DESIGN.md):

text
# Design: Authentication System

## Problem Statement
Users need secure access to API endpoints.

## Architecture Decisions
- **Auth Method**: JWT tokens (vs sessions)
  - Pro: Stateless, scales better
  - Con: Token revocation complexity
- **Storage**: PostgreSQL users table
- **Middleware**: Custom JWT validator

## API Contracts
POST /auth/login → {token, expires_at}
GET /api/* → requires Authorization header

## Data Models
User: id, email, password_hash, created_at

## Success Criteria
- All endpoints require auth except /auth/*
- Tokens expire after 24h
- Password hashing with bcrypt
STAGE 2: Task Breakdown (EXISTING, update)
Update prg plan to accept DESIGN.md:

bash
# From design file
prg plan --from-design DESIGN.md

# Or from scratch (current behavior)
prg plan "Add authentication"
Implementation:

Create src/ai/design_generator.py:

DesignGenerator class

generate_design(user_request: str) -> Design

AI prompt: architecture decisions, trade-offs, API contracts

Update src/ai/task_decomposer.py:

Add from_design(design_path: Path) method

Parse DESIGN.md sections

Generate tasks aligned with design

Add CLI commands to main.py:

prg design <description> --output DESIGN.md

prg plan --from-design DESIGN.md (update existing)

Integration with existing skills:

brainstorming skill → outputs DESIGN.md

writing-plans skill → reads DESIGN.md

subagent-driven-development → executes PLAN.md

Example workflow:

bash
# 1. Brainstorm & design
prg design "Add rate limiting middleware"
# Review DESIGN.md, approve architecture

# 2. Break into tasks
prg plan --from-design DESIGN.md
# Review PLAN.md

# 3. Execute (future feature)
prg execute PLAN.md --auto
Tests:

tests/test_design_generator.py

tests/test_task_decomposer.py (update)

tests/test_two_stage_planning.py (integration)

This matches GitHub Spec-Kit's /speckit.plan + /speckit.tasks workflow.

