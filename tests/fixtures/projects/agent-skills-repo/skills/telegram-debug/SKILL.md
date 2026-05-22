---
name: telegram-debug
description: Inspect Telegram chat IDs, message history, and webhook delivery.
triggers:
  - "telegram webhook failing"
  - "what is my chat id"
  - "show recent messages"
---

# Telegram Debug

Diagnose Telegram delivery issues without touching the bot codebase.

## Process

1. Call `getWebhookInfo` against the bot token.
2. If `last_error_message` is set, surface it with timestamps.
3. Offer a `setWebhook` retry once the upstream is healthy.
