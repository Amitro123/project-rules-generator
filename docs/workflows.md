# Common Workflows

Here are the most common ways to use Project Rules Generator in your daily development.

## 1. Initial Setup

**Goal**: Get your project ready for AI-assisted development.

1.  **Install**:
    ```bash
    pip install -e .
    ```
2.  **Generate Rules + Skills**:
    ```bash
    prg analyze . --mode ai --api-key YOUR_KEY
    ```
3.  **Verify Output**:
    ```bash
    ls .clinerules/
    ```

## 2. Daily Development

**Goal**: Keep your rules up-to-date with your code changes.

1.  **Quick Update**:
    Run this after changing dependencies or adding new files.
    ```bash
    prg analyze . --incremental
    ```
2.  **Plan New Feature**:
    Get AI help breaking down a complex task.
    ```bash
    prg plan "Add rate limiting middleware"
    ```
    ```
3.  **Complex Feature Planning (New)**:
    For larger features, use the two-stage workflow.
    ```bash
    # Stage 1: Generate Architecture Design
    prg design "Add authentication system"

    # Stage 2: Generate Implementation Plan from Design
    prg plan --from-design DESIGN.md
    ```
4.  **Update After Implementation**:
    Ensure new patterns are captured.
    ```bash
    prg analyze . --incremental
    ```

## 3. Team Onboarding

**Goal**: Harmonize coding standards across your team.

1.  **Generate Constitution**:
    Create a high-level agreement on coding principles.
    ```bash
    prg analyze . --constitution
    ```
2.  **Share Rules**:
    Check the `.clinerules` directory into git.
    ```bash
    git add .clinerules/
    git commit -m "docs: add AI coding rules"
    ```

## 4. CI/CD Integration

**Goal**: Ensure rules clearly reflect the current state of the main branch.

Add this step to your GitHub Actions workflow (e.g., `.github/workflows/update-rules.yml`):

```yaml
- name: Update project rules
  run: |
    pip install project-rules-generator
    prg analyze . --incremental --no-commit
    git diff .clinerules/  # Fail if rules are out of sync, or auto-commit
```
