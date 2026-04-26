---
created: 2026-04-26
status: approved
type: spec
project: security_monitor
title: security_monitor
---

# Spec: security_monitor

## Problem Statement [REQUIRED]

Operations engineers responding to a security incident currently scan `/var/log/auth.log` by hand. A single brute-force SSH burst can be buried in 50,000 lines of routine noise per host per day, and on the three incidents we logged in Q1 the attacker had been probing for over 24 hours before anyone noticed. There is no automated detection on the bastion fleet today, and the SOC2 Type 2 audit in Q3 will require documented authentication-monitoring controls. Manual review takes 30-90 minutes per incident and produces inconsistent timelines.

## Goals [REQUIRED]

- [ ] Detect brute-force SSH attempts within 60 seconds of the 5th failed login from a single source IP.
- [ ] Surface alerts in the configured Slack channel within 30 seconds of detection (p95).
- [ ] Reduce mean-time-to-detect for the patterns we cover from 4-8h to under 2 minutes.
- [ ] Produce an audit-ready record of every alert (who, what, when, severity) suitable for SOC2 evidence.

## Non-Goals [REQUIRED]

- No web dashboard in v1 — alerts go out via webhook only.
- Not a SIEM replacement; we don't store full log history, only matched events and incidents.
- Does not cover Windows event logs, application logs, or network IDS in v1.
- Not multi-tenant; one instance per host, configured locally.

## Constraints [REQUIRED]

- Must run on the existing Ubuntu 22.04 bastion hosts; no new infrastructure or managed services.
- Python 3.10+ only — matches the rest of the platform tooling.
- Must run as a systemd unit; no daemonization in user code.
- Cannot read `/var/log/auth.log` without elevated privileges; install path requires `setcap cap_dac_read_search` or systemd capability bounding.
- [SOFT] Prefer stdlib over new dependencies; each new dep needs a one-line justification in `requirements.txt`.
- Must produce no more than 1 outbound webhook call per second under normal load.

## Acceptance Criteria [REQUIRED]

- [ ] After 5 failed SSH login attempts from a single source IP within a 60-second window, an alert is fired.
- [ ] The alert payload includes: ISO timestamp, source IP, target user(s), attempt count, log offset.
- [ ] Alerts reach the configured Slack webhook within 30 seconds of detection (measured at p95).
- [ ] Duplicate alerts for the same source IP are suppressed for 10 minutes after the first alert.
- [ ] The service starts via `systemctl start security-monitor`, recovers cleanly from SIGTERM, and restarts on crash.
- [ ] Configuration loads from a single YAML file at `/etc/security-monitor.yaml`; schema validated at startup.
- [ ] Every fired alert is persisted to a local SQLite database at `/var/lib/security-monitor/incidents.db`.
- [ ] `pytest` passes with ≥85% coverage on `security_monitor/detectors/`.
- [ ] A 24-hour staging soak produces zero unhandled exceptions in the journal.

## Edge Cases [REQUIRED]

- Log file rotated mid-read — reopen by inode (compare `os.stat(path).st_ino` after open) and resume at offset 0 of the new file. Don't re-emit alerts for events from the closed file.
- Webhook returns 5xx or times out — retry with exponential backoff (1s, 2s, 4s); after 3 failures, persist the alert to a local fail-buffer table and continue. Replay buffer on next successful call.
- Source IP is IPv6 — store and emit in canonical form (`ipaddress.ip_address(...).compressed`).
- Clock skew between the host and the alert receiver — use the log timestamp from the parsed line, never wall-clock.
- Burst of >1000 events/second from a flood — batch and dedupe within a 100ms window; never drop an event that would have crossed the alert threshold.
- Malformed log line (truncated, mixed encoding) — log a parse error, increment a metric, skip the line. Never crash on parse error.
- First start with no prior offset — begin tailing at end-of-file (do not retroactively process the entire historical log).

## Open Questions [OPTIONAL]

- Q: Do we need to support log rotation by both `logrotate` and `journalctl` in v1, or can we mandate `logrotate` per the platform standard? — owner: amit — by: 2026-05-03
- Q: Retention period for `incidents.db` — 30, 90, or 365 days? — owner: amit — by: before-merge
