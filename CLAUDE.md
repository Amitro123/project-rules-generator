🔥 CASCADE UPGRADE: Design → Plan → Tasks (Production Quality)

**Current:** Generic → Specific chain broken
**Target:** PLAN drives design/task.yaml improvements

**1. MASTER PLAN Template (Specificity):**
PLAN: {project_name} - {goal}
Est: {total}min | Risks: Redis timeout

1. {title} ({est}min)
Files: llm_client.py, tests/test_cache.py
Depends: {#1}

Add Redis async wrapper
Verify: pytest --cov=80%
AC: Cache hit >80%

text

**2. Cascade Logic:**
PLAN.md → feeds TaskDecomposer → task.yaml (files/AC)
PLAN.md → feeds DesignCreator → DESIGN.md (API contracts)

text

**3. Rules:**
- Extract **project name/tech** from scan
- **Specific files** per task (llm_client.py, not "core")
- Measurable **AC** (pytest pass, coverage %)
- **Risks** per task
- **17min total** realistic

**Test Chain:**
prg create-rules . → DESIGN.md (specific)
prg plan . → PLAN.md (detailed)
→ task.yaml (precise files/deps)

text

**UPGRADE CASCADE → Copilot will complete projects!** 🎯✨
