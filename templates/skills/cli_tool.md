### command-analyzer
Analyze CLI commands and suggest improvements.

**When to use:**
- Adding new commands
- Refactoring argument parsing
- Improving UX

**Tools:** exec, read

**Usage:**
```bash
python main.py --help | analyze
```

### cli-test-generator
Generate CLI integration tests.

**When to use:**
- New command added
- Changed argument behavior

**Output:** pytest test cases for all commands
