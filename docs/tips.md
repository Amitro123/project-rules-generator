# Tips & Best Practices

To get the most out of Project Rules Generator, follow these best practices.

## 1. Start Simple
Begin with a basic analysis to verify everything is working before enabling advanced AI features.
```bash
prg analyze .
```
Once comfortable, add `--ai` for deeper insights.

## 2. Default to Incremental
After the initial setup, rely on incremental updates. It's much faster and preserves manual edits better.
```bash
prg analyze . --incremental
```

## 3. Plan Before You Code
Use the planning feature to break down complex tasks. This helps you clarify requirements and gives the AI a better context for generating code.
```bash
prg plan "Refactor the authentication module"
```

## 4. Treat Rules as Code
Commit the `.clinerules/` directory to git. This ensures every developer on your team (and every AI agent they use) is working with the same set of rules and standards.

## 5. Automate Updates
Integrate `prg` into your CI/CD pipeline. Running it in check-mode (with `git diff`) ensures that documentation and rules never drift from the actual code.

## 6. Curate Your Skills
Don't be afraid to manually edit the files in `.clinerules/skills/learned/`. The AI gives you a great starting point, but you know your project best. Refine them to capture subtle team preferences.

## 7. Use Constitution for Onboarding
Generate a `constitution.md` to help new team members understand the "why" behind the code, not just the "how".
