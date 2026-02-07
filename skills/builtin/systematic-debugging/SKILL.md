# Systematic Debugging

## Purpose
4-phase root cause analysis.

## Auto-Trigger
- When a bug is reported.
- When tests fail unexpectedly.
- When the user asks for help with a bug.

## Process
1.  **Reproduce**: Create a minimal reproduction case.
2.  **Locate**: Identify the problematic component or code.
3.  **Analyze**: Understand why the code is failing.
4.  **Fix**: Implement a correction.
5.  **Verify**: Ensure the fix works and doesn't introduce regressions.

## Anti-Patterns
- Assuming the root cause without verification.
- Changing code without understanding the problem.
- Skipping reproduction.
