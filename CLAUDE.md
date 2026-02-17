🔧 PORT COWORK LOGIC: Smart Rules Generator → PRG

**Goal:** Transfer Cowork's intelligent rule creation to PRG rules engine

**Current PRG rules:** Basic README parsing → Generic rules
**Target:** Cowork-level rules (structured, actionable, quality-gated)

**Extract from Cowork:**
1. **Rules Creation Algorithm:**
   - Input: README + code structure + git history
   - Output: .clinerules/rules.md (YAML frontmatter + sections)

2. **Rule Structure** (Cowork quality):
project: multi-agent-system
tech_stack: [python, asyncio, langchain]
priority_rules: [async_patterns, agent_orchestration]

Coding Standards
High Priority
Always use async/await for agent coordination

Architecture
Single orchestrator pattern

text
3. **Intelligence Features:**
   - Tech stack detection → Specific rules
   - Priority scoring (High/Medium/Low)
   - Anti-pattern extraction from git history  
   - Quality validation (completeness, conflicts)

**Deliverables:**
generator/rules_creator.py (CoworkRulesCreator class)

templates/RULES.md.jinja2

tests/test_rules_creator.py (90% coverage)

CLI: prg create-rules .

text

**Integration Flow:**
prg analyze . → Detect tech/context
prg create-rules . → Cowork-quality rules.md
prg verify-rules → Quality score 85%+

text

**Examples to Generate:**
FastAPI project → REST patterns, Pydantic validation
Multi-agent → Async coordination, error boundaries
React → Hooks patterns, state management

text

**Extract Cowork rules intelligence → Supercharge PRG rules!** 📜🚀
