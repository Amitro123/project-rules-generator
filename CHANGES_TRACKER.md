# Changes Tracker - Skill Orchestration
Date: 2026-02-06

## Modified Files
- `generator/sources/awesome.py`: [NEW] Recursive discovery source.
- `generator/sources/learned.py`: [NEW] Learned skills source.
- `generator/sources/builtin.py`: [NEW] Builtin templates source.
- `generator/orchestrator.py`: [NEW] Central orchestration logic.
- `generator/types.py`: [MOD] Added `source`, `priority` fields.
- `prg_utils/config_schema.py`: [MOD] Added `SkillSourcesConfig` models.
- `config.yaml`: [MOD] Added `skill_sources` section.
- `README.md`: [MOD] Major documentation update (Orchestration, Installation, Flow Diagram).
- `tests/test_conflict_resolution.py`: [NEW] Priority tests.
- `tests/test_sources.py`: [NEW] Source discovery tests.
- `tests/fixtures/`: [NEW] Test data for E2E simulation.

## Verification
- **Test Suite**: `pytest` (61 passed).
- **E2E Simulation**: Verified specific override scenarios (Learned > Awesome > Builtin).
- **Docs**: Visual inspection of README flow diagram.
