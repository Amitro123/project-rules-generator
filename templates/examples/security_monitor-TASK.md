---
created: 2026-04-26
status: ready
type: task
project: security_monitor
title: Implement LogTailer with inode-aware rotation
---

# Task: Implement LogTailer with inode-aware rotation

## Summary [REQUIRED]

Add a `LogTailer` class in `security_monitor/io/tailer.py` that streams new lines from `/var/log/auth.log` as they appear, exposing them as an async iterator. Reopens by inode when the file is rotated.

## Context [REQUIRED]

Implements the log-ingestion piece of [[security_monitor-SPEC]]. The detector module (separate task) consumes lines via `async for line in tailer.stream_lines()` and decides whether each line trips a rule. The tailer must survive `logrotate` without dropping or duplicating lines and must not retroactively replay history on first start. Existing pattern to mirror: `prg_utils/file_watcher.py` uses the same polling-with-aiofiles approach for non-rotating files.

## Steps [REQUIRED]

- [ ] 1. Create `security_monitor/io/__init__.py` and `security_monitor/io/tailer.py` with the `LogTailer` class skeleton.
- [ ] 2. Define `LogLine` dataclass: `path: Path`, `inode: int`, `offset: int`, `timestamp: datetime`, `raw: str`.
- [ ] 3. Implement `__init__(self, path: Path, *, poll_interval: float = 0.25)` and `async def open(self)` that records the starting inode and seeks to end-of-file.
- [ ] 4. Implement `async def stream_lines(self) -> AsyncIterator[LogLine]` using `aiofiles` — read available lines, yield them, sleep `poll_interval`, repeat.
- [ ] 5. On each iteration, `os.stat(self.path).st_ino`. If it differs from the recorded inode, close the old handle, open the new file at offset 0, update the recorded inode, and continue.
- [ ] 6. Handle `FileNotFoundError` during stat or open — log a warning, sleep `poll_interval * 4`, retry. Don't crash.
- [ ] 7. Add structured logging via the existing `loguru` setup — one log line on every reopen with `from_inode`, `to_inode`, `path`.
- [ ] 8. Write unit tests in `tests/io/test_tailer.py` covering: normal append, rotation by rename, rotation by truncate, missing file at start, missing file mid-stream, malformed line bytes.
- [ ] 9. Run `pytest tests/io/ -v` — must pass with no warnings.
- [ ] 10. Run `black .`, `ruff check .`, `isort .` — must pass clean.
- [ ] 11. Add a CHANGELOG.md entry under `Unreleased > Added`.

## Dependencies [REQUIRED]

Blocked by:
- [[security_monitor-SPEC]] — approved.
- Decision on rotation strategy — see Open Question Q1 in the spec; resolved in [[2026-04-26 — Rotation strategy]] (logrotate only).

Blocks:
- [[task-brute-force-detector]] — needs the `LogLine` dataclass shape locked in.
- [[task-systemd-unit]] — needs `LogTailer.open()` exit codes documented.

In parallel with:
- [[task-slack-dispatcher]] — independent; no shared types beyond `LogLine`.

## Definition of Done [REQUIRED]

- [ ] All unit tests pass: `pytest tests/io/test_tailer.py -v`.
- [ ] Coverage on `security_monitor/io/tailer.py` ≥ 90%.
- [ ] `black`, `ruff check`, `isort` all clean.
- [ ] CHANGELOG.md updated under Unreleased > Added.
- [ ] Manual smoke test: tail a real `auth.log` on a staging host, run `logrotate -f /etc/logrotate.d/rsyslog`, verify the tailer emits lines from the new file with no duplicates and no missed lines.
- [ ] PR reviewed and approved by one teammate.

## Notes [OPTIONAL]

- Considered using `watchdog` for filesystem events instead of polling; rejected because it's unreliable on NFS-mounted log directories that some bastion hosts use.
- Considered tracking offset via a sidecar file for crash recovery; deferred to a follow-up — first iteration starts at EOF on every restart, which is acceptable per the spec ("First start with no prior offset — begin tailing at end-of-file").
