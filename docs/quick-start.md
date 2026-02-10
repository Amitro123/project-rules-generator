# Quick Start Guide

Get up and running with Project Rules Generator in 5 minutes.

## 1. Installation

Install directly from source:

```bash
git clone https://github.com/Amitro123/project-rules-generator
cd project-rules-generator
pip install -e .
```

Verify the installation:

```bash
prg --version
```

## 2. First Run: Basic Analysis

Run the generator on your project root to create the initial rules:

```bash
cd /path/to/your/project
prg analyze .
```

This will create a `.clinerules/` directory with:
- `rules.md`: Basic coding rules and file structure.
- `clinerules.yaml`: Configuration for the generator.

## 3. Enable AI Power (Optional but Recommended)

To get custom skills and deep analysis, use the AI mode (requires Gemini or Claude API key):

```bash
export GEMINI_API_KEY=your_key_here
prg analyze . --mode ai --auto-generate-skills
```

## 4. Verify Output

Check the generated rules:

```bash
cat .clinerules/rules.md
```

You are now ready to use these rules with your AI agent!
