# Hermes Skills

A collection of reusable AI agent skills for operational debugging and
Telegram bot maintenance. There is no Python application code in this
repository — the deliverable is the `SKILL.md` files themselves.

## Skills

- `usage-inspector` — query the bot's PostgreSQL DB for active users
- `telegram-debug` — inspect chat IDs, message history, webhook health
- `docker-maintenance` — restart containers, prune images, tail logs

## Stack

- Docker (containerized services)
- Telegram (chat platform)
- Linux (target deploy environment)
- YAML (skill manifest format)

## What this is NOT

This is **not** a Python application. There are no `.py` source files
outside of skill documentation prose. Bug context: previously PRG leaked
49 Python skills (`fastapi-async-patterns`, `pydantic-validation`,
`gitpython-ops`, `argparse-patterns`, etc.) into `.clinerules/skills/learned/`
even though `tech_stack` correctly omitted Python. See `ListOfBugs/Bugs.md`.
