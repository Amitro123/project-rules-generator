# Leftovers — Deferred from Code Review

Items from the code-reviewer agent (second CR pass) that were not fixed yet.
HIGH-1 and HIGH-2 are resolved. Everything below is deferred.

---

## ~~HIGH-3~~ — `tech/profiles.py` split into `_profiles/` subpackage ✓ DONE

**File:** `generator/tech/profiles.py`
**Issue:** Single 682-line file containing all `TechProfile` entries as a flat Python list.
Purely static data with no logic; makes contributor onboarding harder than necessary.
**Fix:** Split by category into `generator/tech/profiles/` subpackage; `profiles.py` becomes
a thin aggregator re-exporting `_PROFILES`. No consumer changes required.

---

## MEDIUM items — all resolved ✓

### ~~MEDIUM-1~~ — f-strings in logger calls (opik_client.py) ✓ DONE
**File:** `generator/integrations/opik_client.py` lines 32, 34, 98, 101
**Issue:** `logger.info(f"...")` evaluates the string even when the log level is disabled.
Rest of the codebase uses `%`-style formatting.
**Fix:** Change to `logger.info("...: %s", value)` pattern.

### ~~MEDIUM-2~~ — f-string in logger.error (sources/learned.py) ✓ DONE
**File:** `generator/sources/learned.py` line 114
**Issue:** Same f-string-in-logger pattern as MEDIUM-1.
**Fix:** Same — use `%`-style.

### ~~MEDIUM-3~~ — Overly broad `except Exception` in skill_discovery.py ✓ DONE
**File:** `generator/skill_discovery.py` lines 155–158
**Issue:** Catches `Exception` instead of `(OSError, shutil.Error)` for file-copy failures.
Currently acknowledged with `# noqa` as non-fatal but can be narrowed.
**Fix:** Replace with `except (OSError, shutil.Error)`.

### ~~MEDIUM-4~~ — Emoji in log messages (ralph/engine.py, rules_git_miner.py) ✓ DONE
**Files:** `generator/ralph/engine.py`, `generator/rules_git_miner.py`
**Issue:** Emoji in `logger.*` calls can cause encoding issues in log aggregators
and non-UTF-8 terminals.
**Fix:** Move emoji to `click.echo()` CLI output only; use plain text in logger calls.

### ~~MEDIUM-5~~ — No file size limit on project file reads ✓ DONE
**Files:** `generator/analyzers/structure_analyzer.py`, `generator/extractors/code_extractor.py`
**Issue:** Files read with `read_text()` without a size cap. `importers.py` already has
`MAX_IMPORT_FILE_SIZE = 1 MB`; these modules don't.
**Fix:** Add a size guard before reading (e.g. skip files > 1 MB with a warning).

---

## LOW items

### LOW-1 — Missing return type annotations on public API functions
**Files:** `generator/skills_manager.py:142`, `generator/interactive.py`
**Issue:** Public functions missing return type hints; inconsistent with rest of codebase.
**Fix:** Add `-> Optional[...]` / `-> None` annotations.

### LOW-2 — f-string in Opik trace logger (duplicate)
**File:** `generator/integrations/opik_client.py` line 98
**Issue:** Duplicate of MEDIUM-1 in the trace-logging path.
**Fix:** Same as MEDIUM-1.
