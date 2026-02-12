# Output Structure

Project Rules Generator consolidates all generated files into a single `.clinerules/` directory inside your project. This keeps your root directory clean and makes it easy to manage rules.

```
.clinerules/
├── rules.md              # Main coding rules
├── rules.json            # Machine-readable rules
├── auto-triggers.json    # Skill activation phrases 🆕
├── constitution.md       # High-level principles
├── clinerules.yaml       # Lightweight config
└── skills/
    ├── project/          # Project-specific overrides 🆕
    ├── learned/          # Global learned skills
    └── builtin/          # Core skills
```

## File Descriptions

-   **`rules.md`**: The core rules file. Contains critical "DOs" and "DON'Ts", testing instructions, dependency information, and architectural overview. This is always generated.
-   **`rules.json`**: Machine-readable version of rules for IDE integrations.
-   **`auto-triggers.json`**: A lookup file mapping phrases to skill names. Used by `prg agent`.
-   **`constitution.md`**: A higher-level document focusing on coding philosophy and long-term principles.
-   **`clinerules.yaml`**: Configuration file for active skills and settings.
-   **`skills/`**:
    -   **`project/`**: Overrides specific to this repository (High Priority).
    -   **`learned/`**: Your global library of learned skills (Medium Priority).
    -   **`builtin/`**: Core PRG skills (Low Priority).
-   **`.prg-cache.json`**: An internal cache file used to speed up incremental updates. It should be added to `.gitignore`.
