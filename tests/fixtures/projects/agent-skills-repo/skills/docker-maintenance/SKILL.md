---
name: docker-maintenance
description: Restart containers, prune images, tail logs.
triggers:
  - "restart hermes container"
  - "prune docker images"
  - "tail bot logs"
---

# Docker Maintenance

Operational toolbox for the Hermes deployment stack.

## Process

1. `docker compose ps` — list services and health states.
2. For the target service: `docker compose restart <name>`.
3. If logs are needed: `docker compose logs --tail=200 -f <name>`.
