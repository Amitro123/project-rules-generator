🚀 FINAL SKILLS ARCHITECTURE: Global + Learned + Project Overrides

**Structure:**
GLOBAL CACHE (~/.project-rules-generator/):
├── builtin/ # PRG core (mcp-server, code-review)
└── learned/ # Cross-project (fastapi, perplexity, react)

PER-PROJECT (.clinerules/skills/):
├── builtin/ → symlink ~/.project-rules-generator/builtin
├── learned/ → symlink ~/.project-rules-generator/learned
└── project/ → NEW for this project only

text

**skills_manager.py:**
```python
GLOBAL_BUILTIN = "~/.project-rules-generator/builtin"
GLOBAL_LEARNED = "~/.project-rules-generator/learned'
PROJECT_LOCAL = ".clinerules/skills/project"

# Setup symlinks
symlink(GLOBAL_BUILTIN, ".clinerules/skills/builtin")
symlink(GLOBAL_LEARNED, ".clinerules/skills/learned")

# Project-specific
generate_project_overrides(PROJECT_LOCAL, readme_content)
Skill Lookup Priority:

python
1. .clinerules/skills/project/ (local override)
2. .clinerules/skills/learned/ (global learned) 
3. .clinerules/skills/builtin/ (PRG core)
Agent Flow:

text
1. Check project/ → fastapi-override.md? Use it
2. Check learned/ → fastapi.md? Use global
3. Check builtin/ → generic-cli.md? Fallback
4. Missing → generate new learned/fastapi.md (reusable!)
TEST:

text
ls ~/.project-rules-generator/learned/  # fastapi, react
ls .clinerules/skills/project/          # project-override
prg analyze --list-skills               # 3 tiers shown
Files: skills_manager.py (symlinks + priority), main.py (list-skills)

text

***

## 🎯 **Agent Decision Flow:**

Need fastapi skill?
├── project/fastapi-override.md → Use ✓
├── learned/fastapi.md → Use global ✓
└── builtin/cli → Generate learned/fastapi.md → Reuse!

