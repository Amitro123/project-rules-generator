---
created: <% tp.date.now("YYYY-MM-DD") %>
status: draft
type: spec
project: <% tp.file.folder() %>
title: <% tp.file.title %>
variant: short
---

# Spec: <% tp.file.title %>

<!--
TEMPLATE: SPEC.short.md (3-section quick variant)
WHEN TO USE: Small, well-understood changes (~1 day or less). For anything
larger or anything affecting >1 person, use SPEC.md.
VALIDATION: All three sections are [REQUIRED]. Acceptance Criteria must
contain >=1 checkbox. No `<!-- GUIDE -->` comments may remain.
-->

## Problem & Goal [REQUIRED]

<!--
GUIDE: One short paragraph (2-4 sentences). Combine: what's broken/missing,
who feels it, and what the fix should achieve. No design choices.
RULES:
  - State the user-visible problem first.
  - End with one sentence on the desired outcome.
EXAMPLE:
  Auth.log on the bastion host scrolls 50k lines/day with mixed noise; a brute-force
  attempt is invisible until someone manually greps. We want a small daemon that
  flags >=5 failed logins from one IP in 60s and alerts via Slack within 30s.
STATUS: [REQUIRED]
-->

## Acceptance Criteria [REQUIRED]

<!--
GUIDE: 3-7 checkable items defining "done".
RULES:
  - Each item is testable — you can imagine the test that proves it.
  - Reference concrete values, paths, or behaviors.
FORMAT:
  - [ ] ...
EXAMPLE:
  - [ ] >=5 failed SSH attempts from one IP within 60s triggers an alert.
  - [ ] Alert reaches the configured Slack webhook within 30s (p95).
  - [ ] Duplicate alerts for the same IP are suppressed for 10 minutes.
  - [ ] `pytest` passes; coverage on the detector >=85%.
STATUS: [REQUIRED] — must contain at least 1 checkbox.
-->

## Risks & Edge Cases [OPTIONAL]

<!--
GUIDE: 1-4 things that could go wrong or that the implementation must handle.
RULES:
  - Format: "X happens — handled by Y" or "Risk: X — mitigation: Y".
  - Skip the section entirely if there's truly nothing here. (Most of the time there is something.)
EXAMPLE:
  - Log file rotates mid-tail — reopen by inode at offset 0.
  - Webhook 5xx — retry 3x with backoff, then drop with a local error log.
  - Risk: false positives during automated test sweeps — mitigation: maintainable allowlist of known scanner IPs.
STATUS: [OPTIONAL]
-->
