# 🚀 PRG v1.1 DEVELOPMENT - Analyzer Agent + Advanced Plan Mode

## 🎯 PRIORITY ORDER (Implement one-by-one):

### **PHASE 1: Analyzer Agent (Quality Scoring)**
Create: src/ai/content_analyzer.py

Input: filepath, content

Output: dict{score: 0-100, breakdown: {}, suggestions: [], patch: str}

Criteria (5 categories x20 pts):

Structure: Headers, logical flow, no empty sections

Clarity: Precise language, no fluff

Project Grounding: References actual files/tools/commands

Actionability: "How to act" not just theory

Consistency: Terminology, format matches project

Create CLI: prg analyze --quality-check [--auto-fix]

Scans all .clinerules/ files

Shows score table

--auto-fix: applies patches in-place

Add to main analyze flow: run quality check after rules/skills generation

text

**TEST:**
```bash
prg analyze . --quality-check
# Expected:
# rules.md: 92/100 ✅ Excellent
# constitution.md: 78/100 ⚠️ Needs fixes
PHASE 2: Advanced Plan Mode
text
1. Enhance prg plan with modes:
   prg plan --from-readme README.md → PROJECT-ROADMAP.md
   prg plan "Fix config bug" → PLAN-config-bug.md
   
2. PLAN format with checkboxes:
Task 1: Reproduce bug
 Run failing command

 Screenshot error

text
   
3. Add prg plan --status → shows progress:
3/7 tasks done
Blocking: Task 4 (tests)

text

**TEST:**
```bash
prg plan --from-readme README.md
prg plan "Add Redis cache"
prg plan --status
PHASE 3: Execution Agent (OPTIONAL)
text
prg execute PLAN.md [--dry-run | --require-approval]
- Loads PLAN.md tasks
- Executes using skills/rules
- Shows diff per task
🛠️ IMPLEMENTATION GUIDE:
1. Content Analyzer Structure:
python
class ContentAnalyzer:
    def analyze(self, filepath: str, content: str) -> QualityReport:
        # 5 criteria scoring
        # Generate patch if score < 85
        return QualityReport(...)
2. CLI Integration:
python
@click.command()
@click.option('--quality-check', is_flag=True)
@click.option('--auto-fix', is_flag=True)
def analyze(quality_check, auto_fix):
    if quality_check:
        analyzer = ContentAnalyzer()
        for file in clinerules_files():
            score = analyzer.analyze(file, read_file(file))
            print(f"{file}: {score}/100")
            if auto_fix and score < 85:
                analyzer.apply_fix(file)
3. Plan Modes:
python
PLAN_MODES = {
    'from-readme': generate_project_roadmap,
    'manual': generate_manual_plan,
}

@click.command()
@click.argument('query', required=False)
@click.option('--from-readme')
def plan(query, from_readme):
    if from_readme:
        generate_project_roadmap(readme_path)
    elif query:
        generate_manual_plan(query)
📋 FILES TO CREATE/UPDATE:
text
✅ src/ai/content_analyzer.py (NEW)
✅ src/cli/analyze.py (ENHANCE)
✅ src/planning/project_planner.py (NEW)  
✅ src/planning/plan_parser.py (NEW)
✅ tests/test_content_analyzer.py (NEW)
✅ tests/test_plan_modes.py (NEW)
✅ README.md (Update features section)
🧪 ACCEPTANCE CRITERIA:
text
Phase 1 ✅
[ ] prg analyze . --quality-check → shows scores table
[ ] rules.md gets 90+ score
[ ] --auto-fix improves low-score files

Phase 2 ✅  
[ ] prg plan --from-readme → PROJECT-ROADMAP.md with phases
[ ] prg plan "Fix bug" → PLAN-bug.md with checklist
[ ] prg plan --status → 3/7 tasks done

Phase 3 (Optional) ✅
[ ] prg execute PLAN.md --dry-run → shows diffs
🎯 START WITH PHASE 1 NOW!
text
1. src/ai/content_analyzer.py
2. CLI integration  
3. Test with existing rules/skills files

Commit: "feat: analyzer agent + quality scoring"
Execute Phase 1 → test → Phase 2 → test → release v1.1.0

