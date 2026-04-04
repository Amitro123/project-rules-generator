# Quick Start Guide

Get up and running with Project Rules Generator in under 5 minutes.

## 1. Installation

```bash
git clone https://github.com/Amitro123/project-rules-generator
cd project-rules-generator
pip install -e .
```

Verify:

```bash
prg --version
```

## 2. First Run (Recommended)

The `init` command is the easiest way to start. It detects your stack, checks
for API keys, and generates your first `rules.md`:

```bash
cd /path/to/your-project
prg init .
```

**What happens:**
- Detects language and framework (Python, Node, Go, etc.)
- Shows whether an API key is configured
- Generates `.clinerules/rules.md` from your README
- Prints next steps

**No API key?** `prg init` still works — it generates rules from your README
and file structure. You get a tip on how to add a key for richer output.

## 3. Manual Analysis

If you prefer the full control of the analyze command:

```bash
prg analyze .
```

Output in `.clinerules/`:
- `rules.md` — coding rules and patterns
- `auto-triggers.json` — skill trigger index
- `skills/` — generated skill files

## 4. Enable AI Power (Optional)

Set a free API key for deeper analysis and AI-generated skills:

```bash
# Option A: Gemini (recommended, free tier available)
export GEMINI_API_KEY=your_key_here
# Get key: https://aistudio.google.com/app/apikey

# Option B: Groq (free, very fast)
export GROQ_API_KEY=your_key_here
# Get key: https://console.groq.com/keys

# Then run full AI analysis
prg analyze . --mode ai --auto-generate-skills
```

## 5. Explore Your Skills

```bash
# List all generated skills
prg skills list .

# Validate a specific skill
prg skills validate pytest-testing .

# Inspect a skill's content
prg skills show pytest-testing .
```

## 6. Create Better Rules

```bash
prg create-rules .
```

This runs the Cowork-powered rules creator with quality scoring and a rich
report. Accepts `--tech fastapi,pytest,docker` to override auto-detection.

---

## Next Steps

| Goal | Command |
|------|---------|
| Add README-based rules | `prg create-rules .` |
| Full AI analysis + skills | `prg analyze . --mode ai` |
| Plan a new feature | `prg plan "Add Redis cache"` |
| Autonomous feature loop | `prg ralph "your task"` |
| See all commands | `prg --help` |

See [cli.md](cli.md) for the full command reference.
