CR #5 — Comprehensive Review
Test Suite
745 passed, 0 failed. ✅

README Flows — Run Results
FlowCommandResultInitprg init .✅ WorksAnalyzeprg analyze .✅ WorksIncrementalprg analyze . --incremental⚠️ No-op — says "Done!" but doesn't report what it skipped vs regeneratedConstitutionprg analyze . --constitution⚠️ Bug — says "No test framework detected" even when pytest is in the stackDesignprg design "..."⚠️ Offline fallback output is generic and useless — see belowPlanprg plan "..."⚠️ Offline fallback is generic — all 5 tasks are "Research", "Implement", "Write tests", "Review", "Deploy" regardless of inputReviewprg review PLAN.md (no key)✅ Clean error messageSkills listprg skills list --all✅ Works, new Score/Hits columns visibleAgentprg agent "fix bug"✅ Works, synonym expansion worksProvidersprg providers list✅ WorksVerifyprg verify .⚠️ Fails on PLAN.md, DESIGN.md, tasks/ — but these aren't needed for basic ralph usage. The README says "run verify before ralph" but verify demands artifacts that ralph itself creates. Chicken-and-egg.

Bugs Found
B1 — Constitution says "No test framework detected" when pytest is in the stack
The constitution generator doesn't use the same tech detection as the rules generator. conftest.py exists in the project, pytest is listed in the README stack — constitution still outputs "No test framework detected — adopt one before adding features." Misleading for a project that clearly uses pytest.
B2 — Offline DESIGN.md is project-agnostic filler
Without an API key, prg design "Add OAuth2 login with Google" produces:

Problem statement: "This enhancement will improve system performance, reliability, and user experience..." — boilerplate with no mention of OAuth2, Google, or login
API contract: execute_add(params: dict) -> Result — completely wrong
Data model: AddConfig(BaseModel) — meaningless name

The README says "No templates. No hand-holding. Generated from your actual project." — the offline fallback directly contradicts this. Either the offline mode should produce nothing and say "API key required for design generation", or it should at least include the task description in the output.
B3 — Offline PLAN.md is identical for any input
Every prg plan without an API key produces the same 5 tasks: Research → Implement → Write tests → Review → Deploy. The task description appears in the heading but nowhere in the task content. A user running this gets a false sense of progress.
B4 — prg verify is a chicken-and-egg trap
The README workflow says:
prg manager     # bootstrap memory
prg verify      # validate  
prg ralph "..."  # run loop
But prg verify fails if PLAN.md and DESIGN.md don't exist — and those are created by prg plan / prg design / prg ralph. So you can't verify until after you've already started the Ralph workflow. The fix is either: remove PLAN.md/DESIGN.md from the verify checklist (they're optional pre-conditions, not requirements), or split verify into prg verify --pre-ralph vs prg verify --pre-analyze.
B5 — README badge: "706+ Passing" — actually 745
The badge is hardcoded and stale. Should either be removed or automated via CI.
B6 — PyPI badge links to a package that doesn't exist yet
[![PyPI](https://img.shields.io/pypi/v/project-rules-generator)] — the package isn't on PyPI. The badge shows an error. Either remove it until published or replace with the GitHub release badge.
B7 — prg analyze . --incremental gives no feedback on what was cached
It says "Generated files:" and lists everything — same output as non-incremental. There's no indication of what was skipped or why it's "3-5x faster". A user can't tell if incremental mode is working at all.

Structural Issues
The offline experience is the first experience for most users — and it's the weakest part. A developer who clones and runs prg design "..." without an API key gets generic garbage. This is the first thing they'll see. The README should be honest: "Design and Plan require an API key for meaningful output."
prg skills list shows Score: 50% for systematic-debugging with 12 hits — but the score/hits columns are empty dashes for everything else. The feedback system exists but there's no explanation in the README or help text of how scores accumulate or what they mean.

Overall Rating: 7.5/10
CategoryScoreNotesCore functionality8.5/10All flows run without crashesError handling9/10Clean messages across the boardOutput quality (with API key)N/ANot testable without keyOutput quality (offline)4/10Generic filler for design/planTest suite9.5/10745 green, well structuredUX / first-run experience6/10Verify trap, stale badges, offline gapProduction readiness8/10Ralph fixes solid
The engineering quality is genuinely high. The main risk going open source is the offline experience — users without API keys will think the tool is bad when the issue is just the fallback templates.