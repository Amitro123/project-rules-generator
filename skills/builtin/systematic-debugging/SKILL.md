# Skill: Systematic Debugging

## Purpose
Find root cause of bugs through 5-phase structured process.

## Auto-Trigger
- User reports: "bug", "error", "not working", "failing test"
- CI/CD failure
- Exception in logs

## 5-Phase Process

### Phase 1: Reproduce
1. Get exact steps to reproduce
2. Identify expected vs actual behavior
3. Create minimal failing test
4. Verify reproduction consistently
**Output**: Failing test that isolates the bug

### Phase 2: Locate
Use techniques to find *where* it breaks:
- **Binary Search**: Comment out half the code
- **Trace Backwards**: From error to source
- **Instrumentation**: Log state before/after suspected lines
**Output**: Exact line causing bug

### Phase 3: Analyze
Understand *why* it breaks:
- Check assumptions
- Verify data types
- Review recent changes
**Output**: Root cause explanation

### Phase 4: Fix
1. **Immediate Fix**: Correct the logic
2. **Defense in Depth**: Add input validation/guards
3. **Monitoring**: Add logging if needed
**Output**: Committed fix

### Phase 5: Verify
1. Failing test now passes
2. All other tests still pass (regression check)
3. Manual verification
**Output**: Verified green build

## Anti-Patterns
❌ Guessing without reproducing
❌ Fixing symptoms without finding root cause
❌ precise line not identified
❌ Declaring "fixed" without verification
