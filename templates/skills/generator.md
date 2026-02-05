### readme-deep-analyzer
Extract nuanced insights from README files for better generation.

**When to use:**
- Input README is sparse or unstructured
- Need to infer implicit tech stack
- Detect project patterns not explicitly stated

**Steps:**
1. Parse markdown hierarchy (H1-H6)
2. Extract badges for tech hints
3. Analyze code blocks for languages
4. Infer workflows from setup instructions

**Usage:**
```bash
python -m analyzer.readme_parser /path/to/README.md --deep
```
Output: Enhanced project_data JSON with confidence scores

### template-optimizer
Improve generated rules/skills based on project domain.

**When to use:**
- Generated output feels generic
- Project has unique patterns (monorepo, microservices)
- Need domain-specific sections

**Input:** Project type, current template

**Steps:**
1. Load domain-specific template extensions
2. Merge with base template
3. Validate output structure

**Usage:**
```bash
python -m generator.templates optimize --type web_app
```

### self-improve
Meta-skill: analyze and improve this generator's output quality.

**When to use:**
- Periodic quality audit
- After user feedback
- Before releases

**Steps:**
1. Run on 10+ sample projects
2. Compare to hand-written rules
3. Identify common gaps
4. Update templates + parser logic

**Usage:**
```bash
python main.py tests/benchmark/ --evaluate
```
