---
name: usage-inspector
description: Query the bot's PostgreSQL DB for active users in a time window.
triggers:
  - "show active users"
  - "check usage today"
  - "how many users this week"
---

# Usage Inspector

Inspect Hermes bot user-activity tables.

## Process

1. Connect to the Postgres replica (read-only role).
2. Query `chat_messages` grouped by `chat_id` over the requested window.
3. Return user count plus top-10 active chats.
