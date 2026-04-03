PRG Ralph Feature Loop Engine - Complete Roadmap
🎯 Objective
Transform existing prg autopilot from project-wide orchestration to a feature-scoped Ralph Loop that:

Takes a specific task ("Improve UI onboarding", "Add caching layer")

Uses existing .clinerules/ as memory layer

Runs autonomous loop until feature complete or max iterations reached

Creates git branches, PRs, with human gates

🏗️ New Architecture
text
prg feature "Improve UI onboarding"
    ↓
prg plan --feature "Improve UI onboarding" 
    → FEATURE-001/PLAN.md + TASKS.yaml
    ↓
prg ralph run FEATURE-001
    → git checkout -b ralph/FEATURE-001-ui-onboarding
    → [RALPH LOOP STARTS]
        iteration 1: reads PLAN.md + .clinerules/rules.md
                   → skill matching → code changes → git commit
        iteration 2: prg review changes → fix issues
        ...
        iteration N: verify success → create PR → human approval
    → git merge | git reset --hard HEAD~N
📋 Implementation Phases (In Order)
Phase 1: Feature Setup (2-3 hours)
bash
# 1. New command
prg feature "Improve UI onboarding" --project .
# Output: 
# - FEATURE-001/PLAN.md 
# - FEATURE-001/TASKS.yaml  
# - FEATURE-001/STATE.json (initial state)
# - git checkout -b ralph/FEATURE-001-ui-onboarding

# 2. Initial state file
FEATURE-001/STATE.json:
{
  "id": "FEATURE-001",
  "task": "Improve UI onboarding", 
  "status": "planning_complete",
  "iteration": 0,
  "tasks_pending": 5,
  "branch": "ralph/FEATURE-001-ui-onboarding",
  "last_review_score": null,
  "exit_condition": null
}
Phase 2: Ralph Loop Core (4-6 hours)
New file: generator/ralph_engine.py

python
class RalphEngine:
    def __init__(self, feature_id: str, project_path: str):
        self.feature_dir = f"{feature_id}"
        self.project_path = project_path
        self.state = self.load_state()
    
    def run_loop(self, max_iterations=20):
        while not self.should_exit():
            self.iteration += 1
            self.execute_iteration()
            if self.verify_success(): 
                self.exit("success")
                break
            if self.state.iteration >= max_iterations:
                self.exit("max_iterations")
    
    def execute_iteration(self):
        # 1. CONTEXT GATHERING
        context = self.build_context()
        
        # 2. SKILL MATCHING  
        skill = self.match_skill(context)
        
        # 3. AGENT EXECUTION
        changes = self.agent_execute(context, skill)
        
        # 4. GIT COMMIT
        self.git_commit(changes, f"ralph iter {self.state.iteration}")
        
        # 5. SELF-REVIEW
        review = prg_review(changes, self.project_path)
        if review.score < 70:
            self.fix_review_issues(review)
    
    def build_context(self):
        return f"""
        PROJECT RULES: .clinerules/rules.md
        FEATURE PLAN: {self.feature_dir}/PLAN.md  
        CURRENT TASK: {self.next_task()}
        PREV COMMITS: git log --oneline -5
        FILES CHANGED: git diff --name-only HEAD~1
        """
Phase 3: Exit Detection Logic (2 hours)
python
def should_exit(self):
    return (
        self.all_tasks_complete() or
        self.human_approved() or  
        self.tests_passing() or
        self.max_iterations_reached()
    )

def verify_success(self):
    checks = [
        prg_review(f"{self.feature_dir}/*").score > 85,
        self.run_tests().passed,
        self.coverage_delta() > 0,
        len(self.pending_tasks()) == 0
    ]
    return all(checks)
Phase 4: New CLI Commands (1 hour)
bash
prg feature "Improve UI onboarding"           # setup + plan
prg ralph run FEATURE-001                     # start loop
prg ralph status FEATURE-001                  # show progress  
prg ralph resume FEATURE-001                  # continue interrupted
prg ralph stop FEATURE-001 --reason "TBD"     # emergency stop
prg ralph approve FEATURE-001                 # human approval → merge
Phase 5: Git Integration (1-2 hours)
bash
# Each iteration:
git checkout ralph/FEATURE-001-ui-onboarding  
git add .
git commit -m "ralph iter 3/12: implement task 2.3 - form validation"

# On success:
gh pr create --title "Ralph: Improve UI onboarding" --body "Auto-generated"
🎛️ Loop Parameters (STATE.json)
json
{
  "feature_id": "FEATURE-001",
  "branch_name": "ralph/FEATURE-001-ui-onboarding", 
  "max_iterations": 20,
  "iteration": 3,
  "tasks_total": 12,
  "tasks_complete": 3,
  "last_review_score": 82,
  "test_pass_rate": 94,
  "exit_condition": null,
  "human_feedback": null
}
🔧 Integration with Existing PRG
PRG Feature	Ralph Usage
prg analyze --incremental	Pre-loop baseline
prg plan --feature	Initial TASKS.yaml
.clinerules/rules.md	Loop context injection
prg skills match	Auto-trigger skills
prg review	Every iteration gate
prg watch	Live feedback
✅ Success Criteria
Loop runs autonomously 10+ iterations

Creates valid git commits

Self-review score > 80% per iteration

Tests pass at end

Human approval flow works

Full CLI commands with status/resume

🚨 Error Handling
text
❌ Max iterations → create PR with findings
❌ Tests fail 3x → human intervention  
❌ Review < 60 → emergency stop + notify
❌ Git conflicts → branch reset + replan
📁 New File Structure
text
.clinerules/                 # existing
features/
├── FEATURE-001/
│   ├── PLAN.md
│   ├── TASKS.yaml
│   ├── STATE.json
│   └── CRITIQUES/          # iteration reviews
├── FEATURE-002/
└── active/                 # symlink to running feature
🚀 First Task for Claude
Start with Phase 1 + 2:

Create generator/ralph_engine.py with RalphEngine class

Add CLI command prg ralph run <feature_id>

Test on demo feature "Add loading states to forms"

Use existing .clinerules/ and PRG commands. Don't change them.

Ready? START CODING.

