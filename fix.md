Agent suggested skill filename fix - implement!

1. Rename .clinerules/skills/learned/error-handling.md → validation-patterns.md

2. Create NEW error-handling.md:
Skill: Error Handling
Purpose
Handle exceptions following project patterns.

Triggers
Exception handling needed

sys.exit() detected

Bare except blocks

DO
Use ProjectRulesGeneratorError for app errors

logging.error() instead of print()

Specific except: except ValueError as e:

Let Click handle CLI exit codes

DON'T
Bare except: Exception

sys.exit() in library code

print() for errors

Example
python
try:
    config = GenerationConfig(**data)
except ValidationError as e:
    logging.error(f"Invalid config: {e}")
    raise ProjectRulesGeneratorError("Config validation failed")

3. Update clinerules.yaml paths.

Test: prg analyze . --list-skills → shows validation-patterns + error-handling


v1.1 Features - Speckit.plan Style + README Improver:

1. **Enhanced prg plan** (Interactive):
prg plan "Add Redis cache" → opens files automatically:

[Open] requirements.txt → +redis

[Create] src/redis_cache.py

[Create] tests/test_redis.py

CLI flags:
--interactive  # Opens files in IDE
--auto-execute # Agent executes tasks

2. **Builtin Skill: readme-improver**
Skill: README Improver
Triggers: "improve README", new feature
Actions:

Extract CLI examples (click --help)

Generate badges (pytest-cov, PyPI)

Add quickstart + usage

Commit README.md

3. **Diagram in README** (Mermaid):
graph TB
A[prg analyze . --ide antigravity] --> B[.vscode/settings.json]
B --> C[Agent Loads Rules + 11 Skills]
D[prg plan "Add feature"] --> E[PLAN.md + Open Files]

Test:
prg plan "Add Redis" --interactive
Agent: "Opening requirements.txt for Task 1..."

Priority: plan enhancement → readme skill → diagram
🎯 v1.0.0 vs v1.1:

v1.0.0 (NOW): 
✅ Agent loads rules + skills ✓
✅ Basic prg plan (5 subtasks) ✓

v1.1 (Future):
✅ Interactive tasks (open files)
✅ readme-improver skill
✅ Speckit.plan workflow