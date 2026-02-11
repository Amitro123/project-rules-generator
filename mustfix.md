CRITICAL BUG: Skills copying broken - creates duplicate SKILL.md instead of real skills!

PROBLEM:
AI matches 11 skills correctly but:
1. builtin/ contains: code-review.md + SKILL.md x2 (generic!)
2. Missing: test-driven-development.md, systematic-debugging.md, etc.
3. index.md shows wrong content

clinerules.yaml shows:
builtin:
- skills/builtin/code-review.md  ✓
- skills/builtin/SKILL.md        ❌
- skills/builtin/SKILL.md        ❌

ROOT CAUSE:
main.py skill copying logic broken:
- Finds matched_skills = ['test-driven-development', 'systematic-debugging', ...]
- Copies generic SKILL.md template instead of actual skill files
- Duplicate copying without validation

FIX (main.py, lines after enhanced_analysis):

```python
# 1. Create directories
builtin_dir = output_dir / 'skills' / 'builtin'
learned_dir = output_dir / 'skills' / 'learned'
builtin_dir.mkdir(parents=True, exist_ok=True)
learned_dir.mkdir(parents=True, exist_ok=True)

# 2. Copy ACTUAL builtin skills (not generic template)
BUILTIN_SKILLS_DIR = Path(__file__).parent / 'skills' / 'builtin'
for skill_name in matched_builtin_skills:  # From enhanced_analysis
    src = BUILTIN_SKILLS_DIR / f"{skill_name}.md"
    if src.exists():
        dst = builtin_dir / f"{skill_name}.md"
        shutil.copy2(src, dst)
        print(f"✓ Copied builtin: {skill_name}")

# 3. Generate learned skills (pytest patterns, etc.)
for skill_path in matched_learned_skills:
    # Generate content from patterns
    generate_learned_skill(learned_dir, skill_path)

# 4. Update index.md with ACTUAL copied skills
generate_skills_index(builtin_dir, learned_dir)

# 5. Update clinerules.yaml paths
update_clinerules_yaml(output_dir / 'clinerules.yaml', builtin_dir, learned_dir)
ACTUAL BUILTIN SKILLS TO COPY:

src/skills/builtin/
├── test-driven-development.md
├── systematic-debugging.md  
├── code-review.md
├── brainstorming.md
├── writing-plans.md
├── subagent-driven-development.md
├── requesting-code-review.md
Expected after fix:

.clinerules/skills/builtin/ → 7+ real skill files
clinerules.yaml → references real files only
ls builtin/ | wc -l → 7+ (not 3 with duplicates)
Test:
prg analyze . --mode ai --provider groq --api-key $GROQ_API_KEY
ls .clinerules/skills/builtin/ # Real skills!
cat .clinerules/clinerules.yaml | grep builtin # No SKILL.md!

