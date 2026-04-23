import pytest
from pathlib import Path
from generator.skills_manager import SkillsManager
from generator.storage.skill_paths import SkillPathManager

def test_extract_project_triggers_filters_by_context(tmp_path, monkeypatch):
    """Verify that extract_project_triggers can filter out irrelevant learned skills."""
    
    # 1. Setup mock global learned directory
    global_dir = tmp_path / "global"
    learned_dir = global_dir / "learned"
    learned_dir.mkdir(parents=True)
    
    # Add a relevant skill
    relevant_dir = learned_dir / "relevant-skill"
    relevant_dir.mkdir()
    (relevant_dir / "SKILL.md").write_text("## Auto-Trigger\n- relevant trigger", encoding="utf-8")
    
    # Add an irrelevant skill
    irrelevant_dir = learned_dir / "irrelevant-skill"
    irrelevant_dir.mkdir()
    (irrelevant_dir / "SKILL.md").write_text("## Auto-Trigger\n- irrelevant trigger", encoding="utf-8")
    
    # Mock SkillPathManager to use our tmp global dir
    monkeypatch.setattr(SkillPathManager, "GLOBAL_DIR", global_dir)
    monkeypatch.setattr(SkillPathManager, "GLOBAL_LEARNED", learned_dir)
    monkeypatch.setattr(SkillPathManager, "GLOBAL_BUILTIN", global_dir / "builtin")
    
    # 2. Initialize SkillsManager
    manager = SkillsManager(project_path=tmp_path / "project")
    
    # 3. Test extraction WITHOUT filtering (current behavior - should show both)
    # Note: we expect this to fail once we implement the fix if we change the default,
    # but for now we follow the existing signature.
    all_triggers = manager.extract_project_triggers()
    assert "relevant-skill" in all_triggers
    assert "irrelevant-skill" in all_triggers
    
    # 4. Test extraction WITH filtering (desired behavior)
    # This will fail now because the parameter doesn't exist yet.
    try:
        filtered_triggers = manager.extract_project_triggers(include_only={"learned/relevant-skill"})
        assert "relevant-skill" in filtered_triggers
        assert "irrelevant-skill" not in filtered_triggers
    except TypeError:
        pytest.fail("SkillsManager.extract_project_triggers does not yet support 'include_only' parameter")
