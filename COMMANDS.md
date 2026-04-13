# Project Rules Generator - Commands Cheat Sheet

Here is a comprehensive list of all `prg` commands available categorized by their functionality.

## 🚀 Analysis & Generation

| Command | Description |
|---------|-------------|
| `prg init .` | First-run wizard: detect stack, generate rules, print next steps |
| `prg analyze .` | Offline generation of rules and structure |
| `prg analyze . --mode ai --auto-generate-skills` | AI-powered analysis and generation of skills |
| `prg analyze . --incremental` | Skip unchanged phases (3-5x faster for large projects) |
| `prg analyze . --constitution` | Generate a high-level coding principles document |
| `prg create-rules .` | Run the Cowork-powered rules creator with quality scoring |

## 🛠️ Skill Management

| Command | Description |
|---------|-------------|
| `prg analyze . --create-skill "skill-name" --ai` | Create a global learned/ reusable skill |
| `prg analyze . --create-skill "skill-name" --scope builtin` | Create a universal builtin pattern skill |
| `prg analyze . --create-skill "skill-name" --scope project` | Create a project-specific skill pattern |
| `prg skills list` | List all available skills |
| `prg skills list --all` | List all available skills including global builtins |
| `prg skills validate <skill-name>` | Run quality checker on a skill (score must be ≥ 90) |
| `prg skills show <skill-name>` | Inspect a skill's content and metadata |
| `prg skills feedback <skill-name> --useful` | Record a successful usage vote for a skill |
| `prg skills stale` | List skills scoring below the 30% useful threshold |

## 🧠 Two-Stage Planning & Specs (Requires AI)

| Command | Description |
|---------|-------------|
| `prg design "Auth system"` | Stage 1: Generate architectural design (`DESIGN.md`) including data models and API contracts |
| `prg plan "Auth system"` | Stage 2: Generate detailed implementation plan (`PLAN.md`) into tasks |
| `prg plan --from-design DESIGN.md` | Create an implementation plan generated directly from an existing design |
| `prg manager .` | Generate a structured `spec.md` for project specifications |

## 🤖 Execution & Autonomous Orchestration

| Command | Description |
|---------|-------------|
| `prg start "Add Redis cache"` | Plan -> Tasks -> Preflight -> Auto-Fix -> Ready fast setup |
| `prg status` | Show task progress table from `TASKS.yaml` |
| `prg exec tasks/001-foo.md` | Execute / complete / skip a task |
| `prg next` | Print the next pending task |
| `prg query` | Query tasks by their status |
| `prg feature "Add OAuth login"` | Set up feature branch and workspace specifically for Ralph |
| `prg ralph run FEATURE-001` | Ralph: Execute the autonomous feature loop |
| `prg ralph approve FEATURE-001` | Ralph: Complete the loop by approving and creating a PR |
| `prg agent "fix a bug"` | Smart Orchestrator simulation (finds which skill best matches) |
| `prg review PLAN.md` | Self-Review artifact for AI Hallucinations / inconsistencies |

## ⚙️ Project Watch & AI Providers

| Command | Description |
|---------|-------------|
| `prg watch .` | Constant directory monitoring to sync files with `.clinerules` |
| `prg watch . --delay 5.0` | Watch directory with a bespoke 5 second debounce string |
| `prg providers list` | Check all configured AI Providers and their status |
| `prg providers test` | Send a test prompt to verify connectivity and print latency |
| `prg providers benchmark` | Run benchmarking standard prompts and rank by latency/quality |
