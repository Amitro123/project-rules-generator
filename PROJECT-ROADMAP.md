# Project Roadmap

Status as of v0.3.0. Items marked ✅ are shipped; 🔄 are in progress; 📋 are planned.

---

## ✅ Shipped (v0.1–v0.3)

- ✅ `prg init` — scaffold `.clinerules/` for any project
- ✅ `prg analyze` — analyze codebase and generate rules + skills
- ✅ `prg create-skill` — generate a single skill from topic name
- ✅ Multi-IDE support: antigravity, cursor, windsurf, claude, gemini
- ✅ Multi-provider AI: Groq, OpenAI, Anthropic, Gemini (with graceful fallback)
- ✅ Strategy chain: AI → README → Cowork → Stub
- ✅ `prg providers benchmark` — measure and rank provider latency
- ✅ `prg ralph` — autonomous feature loop (plan → implement → review → commit)
- ✅ Skills index with quality scoring (heuristic + optional Opik evaluation)
- ✅ PyPI publishing with OIDC trusted publishing
- ✅ 89 test files, 70%+ test-to-source ratio

---

## 🔄 In Progress (v0.4)

- 🔄 Reduce broad `except Exception` in CLI to specific exception types
- 🔄 Reduce module coupling in `skill_pipeline.py` and `rules/creator.py`
- 🔄 Improve `prg watch` reliability under rapid file change events

---

## 📋 Planned

### Near-term
- 📋 `prg update` — refresh existing rules/skills as codebase evolves
- 📋 Web UI for browsing and editing generated skills
- 📋 Skill marketplace — share skills across projects
- 📋 VS Code extension integration

### Longer-term
- 📋 Local LLM support (Ollama)
- 📋 Team sync — shared skill repositories via git
- 📋 Diff-aware rule updates (only regenerate sections that changed)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to pick up a planned item or propose something new.
