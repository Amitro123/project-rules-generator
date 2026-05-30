## Validation Task: Skill Quality & Feature Coverage

Now that bugs A–D are fixed, please run a deeper validation across multiple projects.

### Step 1 — Run on all three projects

```bash
prg analyze . --ai --ide antigravity
```

Run on each of:
- `security_monitor`
- `workshop-agents`
- `gravity-claw-hub` (already done — use existing output)

---

### Step 2 — Check skill quality

For every skill generated in `skills/learned/` and `skills/project/`, verify:

1. **No placeholder text** — no `[One sentence: ...]`, `[placeholder]`, `[list false-positive phrases]`, etc.
2. **Meaningful description** — at least 40 chars, no leading/trailing whitespace
3. **Real triggers** — at least 2 trigger phrases, not generic (`"run"`, `"do"`, `"task"`)
4. **Body has substance** — at least one of: Purpose, Process, Output, Anti-Patterns sections
5. **No empty files** — `os.path.getsize > 0` for every `SKILL.md`

Report: list any skill that fails any of the above checks.

---

### Step 3 — Check feature coverage

For each project, check whether the following features were detected and generated as skills:

| Feature | Expected trigger phrases |
|---|---|
| `spec` | "write spec", "specification", "requirements" |
| `ralph` / planning | "plan", "breakdown", "task list" |
| `design` | "design", "architecture", "system design" |
| `task` | "task", "todo", "implement" |
| `code-review` | "review", "code review", "PR" |
| `test` | "test", "pytest", "jest", "coverage" |
| `debug` | "debug", "fix", "error", "bug" |

For each project, report which features appear in the generated skills and which are missing.
If a feature is consistently missing across all three projects, flag it as a gap in the builtin skill set.

---

### Step 4 — Report format

Please return a table like this:

| Project | Skill | Quality issues | Missing features |
|---|---|---|---|
| gravity-claw-hub | react-components | none | — |
| security_monitor | ... | ... | ... |

Plus a separate section:
**Features missing across all projects:** [list]
**Recommended action:** [add as builtin / improve detection / add to prompts]