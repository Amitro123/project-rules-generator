🔧 EXTRACT COWORK SKILL CREATOR LOGIC → PRG Integration

**Goal:** Port Cowork's smart skill creation to PRG (local/offline)

**What I need from you:**
1. **Skill Creation Algorithm** (pseudocode/python):
   - Input: README/project context
   - Output: Optimized SKILL.md (auto-triggers/tools/steps)
   
2. **Template Engine** (best practices):
${NAME}
Auto-trigger: [...]
Tools: [...]
Steps: [...]
Output: [...]

text

3. **Quality Gates** (Cowork magic):
- Trigger optimization
- Tool selection logic  
- Step decomposition
- Validation checklist

**Deliverables:**
generator/skill_creator.py (full implementation)

templates/SKILL.md.jinja2

tests/test_skill_creator.py

README section: "PRG Skill Creator (powered by Cowork logic)"

text

**Integration:**
prg analyze . → rules + raw skills
prg create-skills → Cowork-quality SKILL.md files
prg export-cowork → Optional Cowork format

text

**Example:**
Input: FastAPI project README
Output: fastapi-security-auditor/SKILL.md
Triggers: ["security audit", "api review"]
Tools: ["ruff", "bandit", "prg review"]

text

**Extract your skill creation intelligence → Make PRG creator Cowork-level!** 🎨
🛠️ מה תקבל אחרי:
text
prg create-skills .  # Offline, token-free!
text
✅ Created 8 project skills (Cowork quality)
├── fastapi-auditor/SKILL.md
├── agent-orchestrator/SKILL.md  
└── test-coverage/SKILL.md
📊 Quality: Triggers 95% | Tools optimal