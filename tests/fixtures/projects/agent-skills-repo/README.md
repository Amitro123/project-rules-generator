# Hermes Skills

A collection of reusable AI agent skills for operational debugging and
Telegram bot maintenance. The deliverable is the `SKILL.md` files themselves —
this is not a Python application.

## Skills

- `usage-inspector` — query the bot's PostgreSQL DB for active users
- `telegram-debug` — inspect chat IDs, message history, webhook health
- `docker-maintenance` — restart containers, prune images, tail logs

## Stack

- Docker (containerized services)
- Telegram (chat platform)
- Linux (target deploy environment)
- YAML (skill manifest format)
