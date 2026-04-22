---
name: gitpython-ops
description: |
  When the user needs to automate Git repository interactions within their Python project.
  When the user is writing scripts to programmatically manage repository state, commits, or branches using gitpython.
  When the user encounters issues with git operations failing silently or unexpectedly in their Python code.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Python
metadata:
  tags: [gitpython, git, automation, repository, python]
---

# Skill: GitPython Operations Workflow

## Purpose

Without a clear, tested workflow for automating Git operations, developers often write brittle scripts that fail silently, leave the repository in an inconsistent state, or don't handle common Git scenarios like merge conflicts or dirty working trees. This skill provides a structured approach to using `gitpython` within your project, ensuring robust and predictable programmatic Git interactions.

## Auto-Trigger

Activate when the user mentions:
- **"automate git with python"**
- **"gitpython script"**
- **"programmatic git operations"**
- **"manage repository in python"**

Do NOT activate for: "git clone", "git commit", "git push" (when referring to manual CLI commands)

## CRITICAL

- Always ensure your `gitpython` scripts are idempotent where possible, meaning they can be run multiple times without causing unintended side effects beyond the first execution.
- Before performing any critical `gitpython` operation (e.g., committing, pushing), verify the repository's state (e.g., no uncommitted changes, correct branch).

## Process

### 1. Initialize the Repository Object

You need to correctly initialize a `gitpython` `Repo` object to interact with your Git repository. Incorrect initialization can lead to `InvalidGitRepositoryError` or unexpected behavior.

```python
import git
import os

# Assuming the script is run from within the repository or a subdirectory
# Or provide an explicit path to the repository
try:
    repo_path = os.getcwd() # Or specify a different path: '/path/to/your/repo'
    repo = git.Repo(repo_path)
    print(f"Successfully initialized Git repository at: {repo.working_dir}")
except git.InvalidGitRepositoryError:
    print(f"Error: No Git repository found at {repo_path}")
    # Handle the error, e.g., exit or create a new repo
except Exception as e:
    print(f"An unexpected error occurred: {e}")

```

### 2. Check Repository Status

It's crucial to understand the current state of the repository before making changes to prevent conflicts or overwriting work. Ignoring the status can lead to lost changes or failed operations.

```python
import git
import os

# Placeholder for existing repo object
try:
    repo = git.Repo(os.getcwd())
except git.InvalidGitRepositoryError:
    print("Error: Not a Git repository.")
    exit(1)

if repo.is_dirty(untracked_files=True):
    print("WARNING: The working directory has uncommitted changes or untracked files.")
    print("Status:")
    # You might want to print the actual status output for detailed view
    # For example, using a subprocess call to 'git status' or iterating through diffs
    # For simplicity, we'll just indicate it's dirty.
    for item in repo.index.diff(None):
        print(f"  Modified: {item.a_path}")
    for untracked in repo.untracked_files:
        print(f"  Untracked: {untracked}")
else:
    print("Working directory is clean.")

print(f"Current branch: {repo.active_branch.name}")
```

### 3. Perform a Git Operation (Example: Adding and Committing)

To ensure changes are properly recorded, you must stage them and then commit. Skipping staging will result in nothing being committed, while skipping the commit will leave staged changes unrecorded.

```python
import git
import os
import datetime

# Placeholder for existing repo object
try:
    repo = git.Repo(os.getcwd())
except git.InvalidGitRepositoryError:
    print("Error: Not a Git repository.")
    exit(1)

# Example: Create a dummy file to commit
dummy_file_path = os.path.join(repo.working_dir, f"dummy_file_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
with open(dummy_file_path, "w") as f:
    f.write("This is a test file for gitpython operations.\n")

print(f"Created file: {dummy_file_path}")

try:
    # 1. Add the file to the staging area
    repo.index.add([dummy_file_path])
    print(f"Added {dummy_file_path} to staging area.")

    # 2. Commit the changes
    commit_message = f"Automated commit: Add {os.path.basename(dummy_file_path)}"
    new_commit = repo.index.commit(commit_message)
    print(f"Successfully committed changes with message: '{commit_message}'")
    print(f"New commit hash: {new_commit.hexsha}")

except git.GitCommandError as e:
    print(f"Error during Git operation: {e}")
    # Handle specific Git errors, e.g., merge conflicts, pre-commit hook failures
except Exception as e:
    print(f"An unexpected error occurred: {e}")
```

### 4. Validate

Validation confirms that the Git operation had the intended effect and the repository is in the expected state. Without validation, silent failures or incorrect states can propagate, leading to hard-to-debug issues later.

```bash
# Check the Git log to see the new commit
git log -1 --pretty=format:"%h - %an, %ar : %s"

# Verify the repository status is clean after the commit
git status
```

## Output

- A clean Git repository status after operations.
- New commits, branches, or other Git objects created as intended.
- Clear error messages if Git operations fail.

## Anti-Patterns

❌ **Don't** perform `gitpython` operations without checking the repository's dirty state or active branch first. This can lead to unexpected conflicts, overwriting uncommitted changes, or applying changes to the wrong branch.
✅ **Do** always check `repo.is_dirty(untracked_files=True)` and `repo.active_branch.name` before starting critical operations to ensure a predictable environment.

❌ **Don't** ignore `gitpython` exceptions. Operations can fail due to various reasons (e.g., network issues for pushes, merge conflicts, invalid paths).
✅ **Do** wrap `gitpython` calls in `try...except git.GitCommandError` and other relevant exception handlers to gracefully manage failures and provide informative feedback.

## Examples

```python
# Example: Using gitpython to pull and push changes
import git
import os

try:
    repo = git.Repo(os.getcwd())
    origin = repo.remotes.origin

    # Ensure the local branch is up-to-date with the remote
    print("Pulling latest changes from origin...")
    pull_info = origin.pull()
    for info in pull_info:
        print(f"  Updated: {info.ref.name} from {info.remote_ref.name}")
    if not pull_info:
        print("  No updates to pull.")

    # After making local changes and committing (as in step 3), push them
    # Ensure there are local commits to push
    if repo.head.commit != origin.refs[repo.active_branch.name].commit:
        print(f"Pushing changes to origin/{repo.active_branch.name}...")
        push_info = origin.push()
        for info in push_info:
            print(f"  Pushed: {info.local_ref.name} to {info.remote_ref.name}")
    else:
        print("No local commits to push.")

except git.InvalidGitRepositoryError:
    print("Error: Not a Git repository.")
except git.GitCommandError as e:
    print(f"Git command error: {e}")
    if "rejected" in str(e):
        print("Push rejected. You might need to pull first or resolve conflicts.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

```