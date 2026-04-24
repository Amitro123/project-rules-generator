Quality Review — hermes-skills output
Files generated
File	Size	Status
.clinerules/clinerules.yaml	538 B	⚠️ incomplete (project skill missing from skills list)
.clinerules/rules.md	2796 B	⚠️ generic, missed domain specifics
.clinerules/rules.json	1749 B	🔴 corrupt (garbage key)
.clinerules/auto-triggers.json	5090 B	🔴 polluted with 20+ irrelevant triggers
.clinerules/skills/index.md	1862 B	⚠️ missing project skill, stale placeholder
.clinerules/skills/project/gemini-api/SKILL.md	~7 KB	✅ real content, minor issues
.agents/rules/hermes-skills.md	2796 B	duplicate of rules.md
🔴 CRITICAL issues (ship-blockers)
C1. rules.json has a corrupt "anti-patterns" key
"🚫_critical_anti-patterns_(never_do_this)": [
  "NEVER run destructive commands (rm -rf, drop table, etc.) ...",       // ← real
  "NEVER generate placeholder comments like 'Implement logic here' ...", // ← real
  "gemini",                                                               // ← YAML fragment
  "skills/builtin/code-review/SKILL.md",                                  // ← YAML fragment
  "skills/builtin/systematic-debugging/SKILL.md",
  "'**/*.pyc'", "'**/__pycache__/**'", "'**/.venv/**'",                  // ← context.exclude
  "'**/node_modules/**'", "'**/*-skills.md'", "'**/*-skills.json'",
  "'**/.clinerules*'",
  "tests/", "docs/",                                                      // ← load_on_demand
  ">"                                                                     // ← literal `>`
]
The md→json converter scrapes every bullet under the heading, but rules.md embeds a <!-- Lightweight Skill References ... --> YAML block after the anti-patterns heading. The key name itself is broken too — sluggified with emoji and parens rather than normalized to critical_anti_patterns.

C2. auto-triggers.json polluted with triggers for skills not in this project
Contains triggers for fastapi-api, gitpython-ops, jinja2-template-workflow, pydantic-validation, argparse-patterns, click-commands, click-cli, readme-driven-workflow, schema-contract-unifier, exception-narrower, god-function-refactor, groq-api, mcp-protocol, database-migrations, fixture-patterns, response-parsing, api-client-patterns, config-management, repo-operations. None apply to hermes-skills.

This is global-learned-cache leakage — extract_all_triggers() walks all globally-available skills instead of the filtered subset. The earlier fix (extract_project_triggers) exists in skills_manager.py but auto-triggers.json appears to still be written from the unfiltered path.

C3. Project skill missing from index + yaml
.clinerules/skills/project/gemini-api/SKILL.md is on disk, but:

clinerules.yaml skills.builtin lists 2 entries; no skills.project key exists
clinerules.yaml skills_count: { builtin: 2, learned: 0, total: 2 } — project skill uncounted
skills/index.md never mentions gemini-api
The thing --ai just generated is invisible to any agent that consumes the metadata.

C4. Wrong project_type: python-cli
hermes-skills is a collection of Claude Code skill directories (each a SKILL.md). No .py sources, no CLI entrypoint. Tech detector appears to default to python-cli on weak signal. Should be agent-skills / claude-skills / docs-only.

⚠️ HIGH issues
H1. Tech stack is shallow — just [gemini]
README explicitly references: Docker (docker exec hermes-agent-...), YAML configs, Linux VPS ops, Telegram Bot, Vite-based Workspace UI, port mappings (8642/3001/3000). Detector missed all of these.

H2. DO/DON'T rules are generic API advice, not Hermes-specific
README has explicit safety rules:

"Never restart a service if an in-place fix is possible"
"Never rewrite config without reading it first"
"Always validate YAML syntax before applying"
"Always prefer docker restart <service> over full stack restarts"
None made it into rules.md. Instead we got generic "Store API keys in .env", "Add retry logic with exponential backoff".

H3. Priorities truncated from 5 → 3
README's Diagnose → Plan → Confirm → Execute → Verify became just Diagnose, Plan, Confirm. Execute and Verify dropped.

H4. Skills index / yaml inconsistent with each other
clinerules.yaml lists 2 builtin skills: code-review, systematic-debugging
skills/index.md lists 6: analyze-code, refactor-module, test-coverage, agent-architecture-analyzer, prompt-improver, (code-review, systematic-debugging missing)
Two code paths generating skill lists with different criteria.

⚠️ MEDIUM issues
M1. skills/index.md has broken template placeholder
### In IDE Agent (Claude/Gemini/Cursor/Antigravity)
Load skills from hermes-skills-skills.md
That file does not exist. Should point to .clinerules/skills/index.md or the per-skill SKILL.md files.

M2. gemini-api/SKILL.md content quality: good-but-flawed
Pros:

Real project-specific content (Hermes Ops Agent context, VPS, AI for log analysis)
Correct anti-patterns (no hardcoded keys, error handling, PII sanitization)
Concrete bash for env-var setup
Cons:

Truncated mid-code-block — the ## Examples section ends at ...{data['contents'][0]['parts'][0 with no closing ``` or ]]}]} — LLM hit max_tokens (2000).
Doesn't use the actual SDK: invents a "conceptual _make_http_request" helper instead of using google-genai / google-generativeai, which Hermes actually depends on (I verified earlier it's installed — hence the Both GOOGLE_API_KEY and GEMINI_API_KEY warning).
Minor hallucinated paths: references api/gemini_integration_conceptual.py, endpoints/agent_task_handler_conceptual.py — no such dirs exist in hermes-skills.
Writes Python source via echo "..." > file.py in bash — works but awkward and brittle with nested quotes.
M3. .clinerules/rules.md.bak + .clinerules/rules.json.bak left behind
Incremental-analyzer backups. Fine for dev, but should be gitignored by the tool's generated .gitignore, or cleaned after merge.

M4. Global ~/.project-rules-generator/learned/ still has test pollution
Files like b.md, conflict-skill.md, test-skill.md, ai-test-skill/, existing-skill/, missing-dep-skill/, fallback-test-skill/, failed-ai-skill/, l.md, test-ai-skill/, test-investigation/, test-skill/, test-skill-2/ leaked from pytest runs that didn't isolate $HOME. The Bug-C blacklist prevents syncing b.md/conflict-skill.md/test-skill.md to builtin/, but these learned/ entries are the source of the Bug H regression and of C2's trigger pollution.

Priority fix recommendations
#	Bug	Severity	Approx fix scope
1	rules.json garbage anti-patterns key	🔴 critical	Fix md→json parser: stop at HTML comment, normalize heading→snake_case, drop emoji
2	auto-triggers.json unfiltered	🔴 critical	Route save_triggers_json() through extract_project_triggers(include_only=...) with the same whitelist used by the index generator
3	Project skill missing from yaml/index	🔴 critical	clinerules.yaml.skills needs a project: key; generate_perfect_index needs to emit project-scoped section
4	Wrong project_type	🟠 high	Tech detector should classify docs-only / agent-skills projects (no .py, no package.json, but README + per-dir SKILL.md → agent-skills)
5	Shallow tech stack	🟠 high	Tech detector should scan README prose for Docker/YAML/Linux/Telegram keywords
6	Generic DO/DON'T	🟠 high	When --ai, mine README "Safety First" / "Priorities" sections for DO/DON'T candidates
7	Priorities truncated 5→3	🟠 high	Priority extractor appears to cap at 3 — remove cap or raise to 7
8	gemini-api SKILL truncated	🟡 med	Raise max_tokens for project-skill generation from 2000 → 4000, or split into sections
9	Global learned pollution	🟡 med	Add prg skills clean-learned command; harden test suite to use isolated $HOME
Bugs 1, 2, 3 are the most damaging — they would actively mislead any agent consuming the files. Bug 4 cascades into bug 5 and 6 (project-type gates which rules/skills get emitted).

