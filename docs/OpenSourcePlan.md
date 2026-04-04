Before You Go Public
1. Security Scan — Do This First
bashgit log --all --full-history -- "*.env" "*.key" "*.pem"
git grep -i "api_key\s*=\s*['\"][a-z0-9]" $(git log --pretty=format:"%H")
Check every commit, not just the current state. API keys committed and deleted are still in git history. If you find any, you need git filter-repo to scrub them — not just a new commit.
Also check:

config.yaml at root — does it have any real values?
.env.example — does it exist? It should, with placeholder values only
.claude/settings.local.json — already in .gitignore, confirm it's not tracked

2. pyproject.toml Has a Fake Email
tomlauthors = [{ name = "Amitro123", email = "amitro123@example.com" }]
@example.com will look unprofessional on PyPI and to contributors. Fix it to a real email or a dedicated OSS one.
3. README Gaps for New Users
The README is good but assumes context. Add:

Badges: CI status (GitHub Actions), PyPI version, Python version — you have the shields syntax already but CI badge needs an actual workflow
A real demo GIF or screenshot — the single highest-impact thing for OSS adoption
"Why not just use X?" section — people will ask why not Cursor rules, .cursorrules, or similar. Answer it upfront
Changelog link is dead for first-time visitors who don't know the project — consider a "What's New" section in README itself

4. GitHub Actions — You Have None
No CI means every contributor PR is unverified. Minimum needed:
yaml# .github/workflows/ci.yml
- pytest on push/PR (Python 3.8, 3.10, 3.12)
- ruff check .
- Black format check
Without this, the README's "run pytest before PR" is just a request you can't enforce.
5. CLAUDE.md Should Not Be in the Public Repo
It contains your internal architecture notes and prompting instructions for Claude. It's not harmful, but it's confusing to outside contributors — they'll think it's a required file for the tool itself. Either remove it or rename it to CONTRIBUTING_CONTEXT.md with a note explaining what it is.
6. docs/AMIT_CODING_PREFERENCES.md
This is personal. It will confuse contributors and looks unprofessional in an OSS repo. Delete it or move content into CONTRIBUTING.md.
7. amitro_todo.md in .gitignore
It's gitignored, but double check it's not tracked:
bashgit ls-files amitro_todo.md

Immediately After Going Public
8. GitHub Repo Settings

Enable branch protection on main: require PR + passing CI before merge
Enable Dependabot for dependency updates
Add topics/tags: ai, developer-tools, cli, llm, rules, agents
Set a short description in the repo header — this is what shows in search results

9. Required Files (GitHub looks for these)
FileStatusNotesLICENSE✅ MITGoodREADME.md✅GoodCONTRIBUTING.md❌ MissingHow to fork, run tests, submit PRCODE_OF_CONDUCT.md❌ MissingStandard for OSS, GitHub auto-links it.github/ISSUE_TEMPLATE/❌ MissingBug report + feature request templates.github/PULL_REQUEST_TEMPLATE.md❌ MissingChecklist for contributorsSECURITY.md❌ MissingHow to report vulnerabilities privately
10. PyPI Publishing
The pyproject.toml is ready but you need:
bashpip install build twine
python -m build
twine upload dist/*  # needs PyPI account + API token
Set up a GitHub Action to publish automatically on version tag:
yamlon:
  push:
    tags: ["v*"]
Also: project-rules-generator as a PyPI name might already be taken — check first. Consider prg-cli or clinerules-generator.

The One Thing That Will Determine Adoption
A working demo that takes under 60 seconds. Right now prg init . on a real project is the demo — make sure it's flawless on a fresh machine with no API key. That's your zero-friction onboarding.
Record a GIF of:
bashcd my-react-project
pip install prg-cli
prg init .
cat .clinerules/rules.md
That GIF in the README is worth more than everything else on this list combined.