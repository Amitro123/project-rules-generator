# PRG End-to-End Audit — Findings

> **Date:** 2026-05-30
> **Method:** Full end-to-end run of every major PRG command against a real,
> unmodified third-party project (`gravity-claw-hub`, a Vite + React + TypeScript
> dashboard), followed by a quality + content review of every generated artifact.
> **Target ground truth:** Vite · React 18 · TypeScript · Vitest · Tailwind CSS ·
> shadcn/ui · TanStack Query · React Router · (Telegram/WhatsApp are *notification
> channels*, not build tech).

This document records what the simulation revealed. It is the rationale behind
**task #12 (P0 — tech-detection grounding)** and the open-source readiness call.

> **Update 2026-05-30 — task #12 RESOLVED.** Tech detection is now grounded in real
> manifests + config-file presence. Re-running detection on `gravity-claw-hub` yields
> `react, react-router, shadcn, tailwindcss, tanstack-query, typescript, vite, vitest`
> — with **no** `jest`, `telegram`, `nextjs`, or `node`. Root cause (§2.1) and the
> telegram-corrupted-AI-artifact path (§2.5) are fixed; the `jest`/`vitest` confusion
> (§2.2) is fixed at the detection layer. See the CHANGELOG "Tech-detection grounding"
> entry. Remaining follow-ups (factual quality scoring §2.2/§2.3, truncation §2.4) are
> tracked separately.

---

## 1. Commands exercised

| Command | Outcome | Note |
|---|---|---|
| `analyze --with-skills` | ✅ generated `rules.md`, `rules.json`, `skills/index.md` + per-project skill snapshot | auto-committed |
| `create-rules --verbose` | ⚠️ self-scored **100/100** | tech: `react, telegram, typescript` |
| `skills list` | ⚠️ leaked the global learned library (46 skills) | unrelated to the target |
| `spec --generate` (Gemini) | ⚠️ `spec.md` **truncated** at 444 chars | Personas/Stories/Criteria missing |
| `design "<feature>"` (Gemini) | ⚠️ `DESIGN.md`, 4 decisions, **0 API/data/criteria** | "truncated" on both attempts |
| `plan --from-design` (Gemini) | ✅ `PLAN.md` (32 subtasks) + `TASKS.json` | detailed, actionable |
| `review DESIGN.md` (Gemini) | ✅ verdict **Needs Revision** + `CRITIQUE.md` | the standout feature |
| `quality .` | ⚠️ `rules.md` **49/100**, `index.md` 79/100 | contradicts create-rules |
| `feature "<feature>"` (Gemini) | ✅ `FEATURE-001` (branch + PLAN + STATE) | isolated in `features/` |
| `verify` | ✅ all preflight checks pass | Ralph-ready |
| `ralph status FEATURE-001` | ✅ clean loop state machine | autonomous loop **not** run (quota/safety) |
| `skills validate react-components` | ⚠️ **97/100 PASS** — but factually wrong | see §2.2 |
| `gaps` | ❌ "No TASKS.yaml found" | `plan` writes `TASKS.json` |

---

## 2. Findings (severity-tiered)

### 🔴 Critical

#### 2.1 Tech detection is the root defect; it poisons every downstream producer
Detector output on the target: `react, telegram, jest, node, typescript`.
Ground truth: `vite, react, typescript, vitest, tailwind, shadcn/ui, tanstack-query, react-router`.

- **False positives:** `telegram` (a notification channel named in the README, not a
  build tech), `jest` (the project uses **Vitest**), `node` (generic).
- **Missed entirely:** Vite, Vitest, Tailwind, shadcn/ui, TanStack Query, React Router.

**Root cause (code-level):**
- `generator/utils/tech_detector.py` → `detect_from_dependencies()` has a hardcoded
  10-entry `node_map` (`react/vue/express/jest/typescript/konva/three/babylon`). It
  has **no knowledge of the modern Vite/Vitest/Tailwind/TanStack/shadcn ecosystem**,
  so `package.json` yields almost nothing beyond `react` + `typescript`.
- `telegram` is classified as `infrastructure` (see `generator/tech/lookups.py`
  `TECH_CATEGORIES` + `tech_detector.py:196`), which makes it a "README-primary" tech —
  so a prose mention of "Telegram" is promoted straight into `tech_stack`.
- There is **no test-runner disambiguation**: `jest` is in the map, `vitest` is not,
  and the presence of `vitest.config.ts` is never consulted.
- `vite` is only reachable via README keyword scraping (not `package.json` deps nor
  `vite.config.ts` presence), so it is silently dropped on projects whose README
  doesn't happen to name it the "right" way.

This is the **systemic pattern**: multiple producers read a shared profile with no
reconciliation against ground truth. `.prg-invariants.json` enforces *internal*
consistency, **not correctness** against the project's actual manifests.

#### 2.2 Quality scores are structural, not factual — confidently-wrong output scores high
The `react-components` project skill scored **97/100 PASS**, yet:
- Repeatedly calls the app a **"Next.js project"** (it's Vite — no `pages/` router).
- Uses **`npx jest`** and tags `jest` (project runs **Vitest** — that command fails).
- Writes components to **`components/`** (project uses `src/components/`).
- Never mentions **shadcn/ui**, the project's actual component system.

The validator's only warning was *"description has leading/trailing whitespace."* It
cannot detect that the framework and test runner are hallucinated. **A tool whose
entire value is generated guidance is scoring fabricated guidance as 97/100.**

#### 2.3 Two quality systems contradict each other on the same file
- `create-rules` → `rules.md` = **100/100 PASSED**
- `prg quality .` → same `rules.md` = **49/100 Poor**

A 51-point disagreement with no shared source of truth. The generated rules are also
generic React boilerplate with cross-stack errors — e.g. *"Add PropTypes or
TypeScript"* (the project is already TypeScript) and *"Add docstrings to all public
functions"* (a Python-ism).

### 🟠 High

#### 2.4 LLM truncation silently degrades AI artifacts
On free-tier Gemini, `spec.md`, `DESIGN.md`, and even `CRITIQUE.md` came out
truncated (mid-sentence cutoffs; missing structured sections). `design` *detects*
truncation ("LLM response looks truncated on attempt 1/2") but still writes the
incomplete result instead of failing loudly or continuing generation.

#### 2.5 A tech false-positive corrupts AI artifacts, not just rules
Because `telegram` was in the tech context, `design` recommended *"Telegram
integration"* for cost alerting as if it were an established channel — fabricated
architecture driven by a detection bug.

### 🟡 Medium / Low

- **`skills list` leaks the maintainer's global learned library** into an unrelated
  project — including PRG-internal skills (`fastapi-api`, `gemini-api`,
  `mcp-protocol`) and junk stubs (`l`, `conflict-skill`, `fallback-skill`,
  `coverage-patterns`). The per-project *snapshot* selection was correctly
  React-relevant; only the global `list` view is noisy.
- **`PLAN.md` Files/Changes mismatch:** subtask 1 says "create `backend/`" but the
  Files field lists `src/`, plus a stray trailing backtick artifact.
- **Ralph branch slug truncated mid-word:** `ralph/FEATURE-001-…-agents-and-`.
- **Manifest-format mismatch:** `gaps` expects `TASKS.yaml`; `plan` emits `TASKS.json`.
- **`skills validate` self-reports a template-fill bug:** leading/trailing whitespace
  in `description`.

---

## 3. What genuinely works well

- **`review`** — correct verdict, caught the missing design sections *and* that the
  design smuggles a Node backend into a frontend-only app. Best-in-class feature.
- **Ralph** — clean state machine, well-isolated `features/FEATURE-001/`, proper
  `STATE.json`, working `verify` preflight.
- **`plan`** — detailed, dependency-ordered decomposition (32 tasks, time estimates).
- **Per-project skill snapshot** — tech-relevant selection (React skills only),
  unlike the global `skills list`.

---

## 4. Open-source readiness verdict

**Ready to make *public* (source-available, accept contributors): yes.**
**Ready to *announce/launch* as a quality tool: not yet — ~2 fixes away.**

- ✅ MIT `LICENSE`, honest `Development Status :: 3 - Alpha` classifier, 1,693 tests
  passing, strong `CONTRIBUTING.md`, real docs, CI, no hardcoded secrets.
- 🔴 **The README's first command fails** — published PyPI wheel is broken
  (`pip install project-rules-generator`). → **task #11 / v0.3.1.**
- 🔴 **Generated output is factually wrong on a vanilla React project** (§2.1–2.3).
  → **task #12 (P0).**
- 🔴 **Marketing overclaims integration:** README says Cursor/Windsurf/Copilot read
  `.clinerules/` "automatically," but only Cline's `.clinerules` + Antigravity are
  actually wired. → CR #9.

**Recommendation:** ship v0.3.1 (fix the wheel), land task #12 (tech grounding), and
soften the multi-IDE claim. Then it is launch-ready. The repo can flip public today
under the explicit Alpha banner with a short "Known limitations" note.

---

## 5. Action plan

| Priority | Item | Task |
|---|---|---|
| P0 | Ground tech detection in real project files (manifests + config presence; separate channels from stack; disambiguate test runner; validate via invariants; add fixtures) | #12 |
| P1 | Publish v0.3.1 to fix the broken PyPI wheel | #11 |
| P1 | Make quality scoring factual (or at least reconcile create-rules vs `prg quality`) | follow-up of §2.2/2.3 |
| P2 | Fail-loud / continue-generation on LLM truncation | §2.4 |
| P2 | Reconcile multi-IDE marketing claim with reality | CR #9 |
| P3 | Scope `skills list` to project-relevant skills; purge junk stubs | §2 medium |
