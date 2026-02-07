# Skill: Systematic Debugging

## Purpose
Find root cause of bugs through 4-phase structured process.

## Auto-Trigger
- User reports: "bug", "error", "not working", "failing test"
- CI/CD failure
- Exception in logs

## 4-Phase Process

### Phase 1: Reproduce
1. Get exact steps to reproduce
2. Identify expected vs actual behavior
3. Create minimal failing test
4. Verify reproduction consistently

**Output**: Failing test that isolates the bug

### Phase 2: Root Cause Tracing
Use techniques:

**A. Binary Search**
- Comment out half the code
- Does bug still occur?
- Narrow down to specific lines

**B. Trace Backwards**
- Start from error point
- Follow data flow backwards
- Find where expectation breaks

**C. Add Instrumentation**
```python
logger.debug(f"State before: {state}")
problematic_function()
logger.debug(f"State after: {state}")
```
**Output**: Exact line/condition causing bug

### Phase 3: Defense in Depth
Don't just fix the symptom:
- **Immediate Fix**: Prevent crash
- **Validation**: Add input checks
- **Monitoring**: Add logging/metrics
- **Prevention**: Add tests for edge cases

### Phase 4: Verification
- Failing test now passes
- All other tests still pass
- Manual verification in UI/CLI
- Check logs for warnings

## Anti-Patterns
❌ Guessing without reproducing
❌ Fixing symptoms without finding root cause
❌ Not adding tests for the bug
❌ Declaring "fixed" without verification
