text
# PRG v2.0 - Ralph-First Architecture Rewrite

## 🎯 GOAL
**Transform PRG from 15-feature complexity to 10-feature Ralph-centric product**

**KEEP**: Analysis, Skills, Incremental, Constitution, Skill Management, Watch, Spec, Review, Tracking
**PROMOTE**: Ralph Feature Loop → Feature #10 (default execution mode)  
**DEPRECATE**: Task Breakdown, Two-Stage Planning, Project Manager, Autopilot (redirect to Ralph)

## 🗑️ IMMEDIATE DEPRECATIONS (Code + Docs)

**Remove these features completely** (no --deprecated flag, just gone):
❌ prg plan --feature → prg ralph "task"
❌ prg design → Ralph internal planning
❌ prg manager → prg ralph discover (new)
❌ prg autopilot → prg ralph run

text

**Update docs/features.md**:
Active Features (10 total):

Basic Analysis ✅

AI Skills ✅

Incremental ✅

Constitution ✅

Skill Management ✅

prg watch ✅

Spec Generation ✅

Self-Review ✅

Skill Tracking ✅

Ralph Feature Loop 🔥 DEFAULT EXECUTION

text

## 🏗️ NEW DEFAULT FLOW
OLD (15 features, confusing)
prg analyze . --ai
prg plan "add auth"
prg manager .
prg autopilot .

NEW (Ralph-First, 3 commands)
prg analyze . --incremental # 10s setup
prg ralph "Add loading states" # autonomous feature
prg ralph approve FEATURE-001 # merge PR

text

## 🔧 CODE CHANGES REQUIRED

### 1. Promote Ralph to Core (2 hours)
```bash
# generator/ralph_engine.py → core/ralph.py (core module)
# Add to cli.py: "ralph" as main entrypoint
# Feature table: Ralph = #10, not #15
```

### 2. Update prg manager → Ralph Wrapper (1 hour)
```python
# generator/project_manager.py
def run(self):
    features = self.discover_features()  # from spec.md / README
    for feature in features:
        subprocess.run(["prg", "ralph", feature])
```

### 3. CLI Command Consolidation (1 hour)
```bash
prg ralph "Add loading states"           # full lifecycle
prg ralph discover                       # manager replacement  
prg ralph run FEATURE-001               # continue specific
prg ralph status FEATURE-001            # progress
prg ralph approve FEATURE-001           # git PR + merge
```

### 4. Update All Docs (30 min)
**features.md**: 10 features only, Ralph = default execution
**README.md**: "Ralph-First" positioning, 3-command flow
**Deprecations**: Clear redirect paths

## 📁 File Structure (Simplified)
.clinerules/ # unchanged
features/ # Ralph workspace
├── FEATURE-001/
│ ├── PLAN.md
│ ├── STATE.json
│ └── CRITIQUES/
└── active/ # symlink

NO MORE: task-plans/, design-docs/, manager-artifacts/
text

## 🎛️ RalphEngine (Keep + Enhance)
```python
class RalphEngine:  # core/ralph.py
    def __init__(self, task: str, project_path: str):
        self.feature_id = self.create_feature(task)
        self.state = StateManager(self.feature_id)
    
    def run(self):  # Replaces: plan + design + execute + review
        self.analyze_project_rules()
        self.generate_feature_plan()
        self.execution_loop()
```

## ✅ SUCCESS CRITERIA
[] prg ralph "Add X" = complete feature lifecycle
[] prg analyze + prg ralph = 2-command daily workflow
[] 10 features total (no deprecated cruft)
[] prg manager → prg ralph discover (non-breaking)
[] README shows 3-command flow
[] Tests pass on demo project

text

## 🚨 DON'T TOUCH
✅ .clinerules/ generation
✅ prg analyze --incremental
✅ prg skills / prg review
✅ Skill tracking
✅ prg watch

text

## 📋 IMPLEMENTATION ORDER
Move ralph_engine.py → core/ralph.py

Add CLI: prg ralph "task"

Update prg manager → ralph wrapper

Remove deprecated commands (plan/design/autopilot/manager)

Update all docs (10 features, Ralph-first)

Test: prg analyze → prg ralph "add loading states"

Tag v2.0.0 "Ralph-First"

text

## 🚀 FIRST COMMAND TO TEST
```bash
prg analyze . --incremental
prg ralph "Add loading states to all forms"
# → should create features/LOADING-STATES/, run 8-12 iterations, create PR
```

---

**Start with step 1: `core/ralph.py` + CLI integration. No breaking changes.**

**Ready? CODE NOW.**
