# Project Rules Generator: Best Practices & How-To Guide

Welcome to the **Project Rules Generator (PRG)**! 

If you are publishing your project as open source, or onboarding a team of developers who rely heavily on AI tools like Cursor, Claude Code, or Copilot, PRG acts as your persistent, shared "AI Brain." 

This guide breaks down the absolute best practices for adopting PRG into your daily development lifecycle.

---

## 1. The Initial Setup (The "First Run")

### Do: Start with the AI Flag
When running PRG for the first time, don't just use the offline analyzer. Supply an API key and explicitly use the `--ai` flag. The LLM adds a layer of semantic understanding that simple Regex cannot match, automatically identifying anti-patterns and extracting sophisticated testing rules from your codebase.
```bash
export GEMINI_API_KEY=your_key_here
prg analyze . --ai
```

### Do: Review and Curate `.clinerules/rules.md`
PRG is built to be smart, but *you* are the domain expert. Once `rules.md` is generated:
1. Open the file.
2. Ensure it explicitly captured your database preferences, variable naming standards, or exact framework versions. 
3. **Commit it to version control.** Your AI agents will read this file automatically on every new session.

---

## 2. Day-to-Day Maintenance

### Run Incremental Updates After Major Changes
Your codebase evolves. Features are added, and new libraries are installed. Ensure your `.clinerules/` memory doesn't go stale. 
Whenever you merge a massive PR or add a new framework, run the incremental caching mode to update your rules lightning fast:
```bash
prg analyze . --incremental
```

### Treat the Constitution as Immutable
If you run `prg analyze . --constitution`, PRG will produce `constitution.md`. This is designed to hold your **non-negotiable** principles (e.g., *Never commit secrets, always type-check with MyPy*). Keep this concise. AI agents suffer from "token blindness" if rules are too long.

---

## 3. Mastering the 3-Layer Skills System

PRG can capture complex, multi-step tasks into executable "skills". 

### Know When to Scope Your Skills
* **Project Layer:** Use this for workflows that only make sense in this exact repository. (e.g. *Deploying to your company's AWS staging environment.*)
* **Learned Layer (The Default):** Use this for personal workflows that you want to travel with you to *other* projects on your computer. (e.g. *A custom TDD scaffolding script.*)
```bash
# Creates a globally reusable skill
prg analyze . --create-skill "FastAPI-TDD-Skeleton" --ai
```

### Run Validations on Manually Written Skills
If you manually edit a YAML/Markdown skill inside `.clinerules/skills/`, it's easy to break the required Schema. Always run the built-in validator to ensure it maintains a minimum 90/100 score:
```bash
prg skills validate my-custom-skill
```

---

## 4. The Orchestrator: Safe Autonomous Execution

PRG comes with a heavily capable Two-Stage Planner and optional Ralph execution loop. To prevent the AI from "running away with your code," stick to this paradigm:

### Best Practice: Always Use Two-Stage Planning
Don't jump straight into code generation on complex tasks. 
1. **Design First:** Generate an architectural approach.
   ```bash
   prg design "Add OAuth2 Authentication"
   ```
   *Review `DESIGN.md`. If it's wrong, change the prompt.*

2. **Plan Second:** Generate granular execution steps.
   ```bash
   prg plan "Add OAuth2 Authentication"
   ```
   *Review `PLAN.md` and `TASKS.json`.*

3. **Execute:** Have the agent run the tasks strictly matching the approved plan.

### Use Self-Review (`prg review`)
Before letting Ralph execute a feature, funnel your `PLAN.md` through the AI evaluator:
```bash
prg review PLAN.md
```
This generates a `CRITIQUE.md` scorecard. It will explicitly call out if the plan forgot to include unit tests, or if it missed a crucial dependency update.

---

## 🚨 General Anti-Patterns

* ❌ **Don't ignore the git state.** Never run `prg ralph "..."` on a dirty working tree. Always make sure your git status is clean before letting autonomous orchestration run, so you can quickly `git status` and revert if it writes bad code.
* ❌ **Don't write huge rule sets.** Keep `.clinerules/rules.md` to the point. If you have a massive block of boilerplate, turn it into a **Skill** instead of a Rule.
* ❌ **Don't leave API Keys hardcoded.** PRG seamlessly reads `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, and `OPENAI_API_KEY` from your environment. Use `export` or a `.env` file instead of passing it in plain text.
