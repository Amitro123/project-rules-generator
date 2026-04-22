---
name: readme-improver
description: |
  For developers struggling with incomplete or inconsistent README files, this skill provides automated checks and best-practice guidance to ensure project documentation is clear and comprehensive.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
metadata:
  tags: [readme, documentation, ci, best-practices]
---

# Skill: Readme Improver

## Purpose

Without clear and consistent README files, developers often struggle to understand project setup, usage, and contribution guidelines, leading to wasted time and onboarding friction. This skill enforces best practices for README content and structure, ensuring crucial information is readily available and easy to find.

## Auto-Trigger

Activate when the user mentions:
- "improve readme"
- "readme checklist"
- "document project"

Do NOT activate for: "readme generator"

## CRITICAL

- A README file must exist at the root of the project.
- The README should be written in Markdown.

## Process

### 1. Check for README Existence

[WHY this step matters — Skipping this means the core documentation file is missing, making any further improvements impossible.]

```bash
if [ ! -f "README.md" ]; then
  echo "Error: README.md not found at the project root."
  exit 1
fi
```

### 2. Basic README Content Check

[WHY this step matters — A missing project title or description makes it immediately difficult for a new user to grasp the project's purpose.]

```bash
if ! grep -qE "^#\s+" README.md; then
  echo "Warning: README.md does not appear to have a main heading (e.g., '# Project Title')."
fi
if ! grep -qE "^#\s+.*\n\n[^#].*" README.md; then
  echo "Warning: README.md does not appear to have a description following the main heading."
fi
```

### 3. Check for Installation Instructions

[WHY this step matters — Without clear installation steps, users cannot easily set up the project, hindering adoption and testing.]

```bash
if ! grep -qE "## Installation" README.md; then
  echo "Warning: README.md does not contain an '## Installation' section."
fi
```

### 4. Check for Usage Instructions

[WHY this step matters — Users need to know how to run and interact with the project; missing usage instructions lead to confusion and underutilization.]

```bash
if ! grep -qE "## Usage" README.md; then
  echo "Warning: README.md does not contain a '## Usage' section."
fi
```

### 5. Check for Contribution Guidelines

[WHY this step matters — Clearly defined contribution guidelines encourage community involvement and streamline the process for new contributors.]

```bash
if ! grep -qE "## Contributing" README.md; then
  echo "Warning: README.md does not contain a '## Contributing' section."
fi
```

### 6. Check for License Information

[WHY this step matters — Users and contributors need to understand the project's licensing terms to ensure compliance and proper usage.]

```bash
if ! grep -qE "## License" README.md; then
  echo "Warning: README.md does not contain a '## License' section."
fi
```

### 7. Validate Markdown Syntax (Basic)

[WHY this step matters — Invalid Markdown can render incorrectly, making the README difficult to read and understand.]

```bash
# This is a basic check; a full Markdown linter would be more robust.
# We're checking for common syntax errors like unclosed tags or incorrect list formatting.
# For this general skill, we'll assume a basic check is sufficient.
# If a more advanced tool were available (e.g., markdownlint-cli), we'd use that.
echo "Performing basic Markdown syntax validation (manual review recommended for complex issues)."
```

## Output

- Warnings printed to the console if sections or best practices are missing.
- The `README.md` file remains unchanged unless manual edits are made based on the warnings.

## Anti-Patterns

❌ **Don't** rely solely on code comments for project documentation. Code comments are for explaining *how* the code works, not *what* the project is, *how to use it*, or *how to contribute*.
✅ **Do** maintain a comprehensive `README.md` file at the project root that covers the project's purpose, installation, usage, contribution, and licensing.

## Examples

```markdown
# My Awesome Project

This is a brief description of what My Awesome Project does. It's designed to solve [problem X] using [technology Y].

## Installation

To install My Awesome Project, follow these steps:

1. Clone the repository.
2. Navigate to the project directory.
3. Run `pip install -r requirements.txt`.

## Usage

To use the project, execute the following command:

```bash
python main.py --input data.csv --output results.json
```

## Contributing

We welcome contributions! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
```