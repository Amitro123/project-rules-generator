Fix the following bugs in the codebase. Do not explain, just fix and run pytest after each fix to confirm green.

N1 — cli/feature_cmd.py:
- Add is_git_repo() check at top of feature() before any work, same pattern as ralph_go in cli/ralph_cmd.py
- Replace feature_dir.mkdir(parents=True, exist_ok=True) with FileExistsError retry loop (5 attempts), same pattern as ralph_go
- Add timeout=30 to the git checkout -b subprocess call
- Import is_git_repo at module level (not inside function) so tests can patch cli.feature_cmd.is_git_repo
- Update tests/test_feature_cmd.py: any test that patches subprocess.run globally must also patch cli.feature_cmd.is_git_repo with return_value=True

N2 — generator/ralph_engine.py, run_loop():
- After self.execute_iteration(), add: if self.state.status in ("stopped",): continue
- This skips the verify_success() call (and its full test suite run) when the loop was emergency-stopped

N3 — cli/cmd_design.py:
- Change DesignGenerator(provider=provider) to DesignGenerator(provider=provider or "groq")

N4 — generator/ralph_engine.py, _detect_test_runner():
- pyproject.toml alone should NOT trigger pytest (false positive on Rust/Node projects)
- Only use pyproject.toml as a pytest indicator if it contains "[tool.pytest" or "pytest"
- Strong indicators (pytest.ini, conftest.py, setup.cfg) still trigger pytest unconditionally

N5 — generator/ralph_engine.py, _save_tasks():
- Make write atomic: write to tasks_yaml.with_suffix(".tmp") then os.replace(tmp, tasks_yaml)
- Same pattern already used in FeatureState.save()

N6 — cli/ralph_cmd.py:
- Add is_git_repo() check to ralph_run() and ralph_resume(), same pattern as ralph_go()
- Raise click.ClickException with clear message if not a git repo

N7 — generator/ralph_engine.py, run_loop():
- Wrap self.execute_iteration() in try/except Exception
- On unhandled exception: set self.state.status = "stopped", self.state.exit_condition = "unhandled_exception", call self.save_state(), then re-raise

After all fixes: pytest must show 0 failed.