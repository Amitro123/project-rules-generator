import pytest

from generator.importers import AgentRulesImporter, VercelSkillsImporter


@pytest.fixture
def agent_rules_pack(tmp_path):
    pack_dir = tmp_path / "my-agent-rules"
    pack_dir.mkdir()

    rule_file = pack_dir / "always-be-kind.mdc"
    rule_file.write_text(
        """---
description: Always be kind to the user
globs: ["**/*"]
---
# Always be kind

You should always be polite and helpful.
""",
        encoding="utf-8",
    )
    return pack_dir


@pytest.fixture
def vercel_skills_pack(tmp_path):
    pack_dir = tmp_path / "vercel-skills"
    pack_dir.mkdir()

    skill_dir = pack_dir / "nextjs-expert"
    skill_dir.mkdir()

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """
# Next.js Expert

You are an expert in Next.js App Router.
""",
        encoding="utf-8",
    )
    return pack_dir


def test_agent_rules_importer(agent_rules_pack):
    importer = AgentRulesImporter()
    pack = importer.import_skills(agent_rules_pack)

    assert pack.name == "my-agent-rules"
    assert len(pack.skills) == 1
    skill = pack.skills[0]
    assert skill.name == "always-be-kind"
    assert skill.description == "Always be kind to the user"
    assert skill.category == "project_rules"
    assert skill.source == "agent-rules"
    assert "**/*" in skill.triggers


def test_vercel_skills_importer(vercel_skills_pack):
    importer = VercelSkillsImporter()
    pack = importer.import_skills(vercel_skills_pack)

    assert pack.name == "vercel-skills"
    assert len(pack.skills) == 1
    skill = pack.skills[0]
    assert skill.name == "nextjs-expert"
    assert skill.category == "vercel_skill"
    assert skill.source == "vercel-agent-skills"
    assert "You are an expert" in skill.usage_example


def test_vercel_importer_truncates_large_file(tmp_path):
    from generator.importers import MAX_IMPORT_FILE_SIZE, VercelSkillsImporter

    skill_dir = tmp_path / "large-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"

    # Create content larger than the limit
    content = "A" * (MAX_IMPORT_FILE_SIZE + 1000)
    skill_file.write_text(content, encoding="utf-8")

    importer = VercelSkillsImporter()
    skill = importer._parse_file(skill_file)

    assert skill is not None
    assert len(skill.usage_example) == MAX_IMPORT_FILE_SIZE
    assert skill.usage_example == content[:MAX_IMPORT_FILE_SIZE]


def test_agent_rules_importer_handles_large_file(tmp_path):
    from generator.importers import MAX_IMPORT_FILE_SIZE, AgentRulesImporter

    rule_file = tmp_path / "large-rule.mdc"

    # Frontmatter fits within the limit, but total file exceeds it
    frontmatter = "---\ndescription: Large rule\nglobs: ['*']\n---\n"
    junk = "B" * MAX_IMPORT_FILE_SIZE
    rule_file.write_text(frontmatter + junk, encoding="utf-8")

    importer = AgentRulesImporter()
    skill = importer._parse_file(rule_file)

    assert skill is not None
    assert skill.description == "Large rule"
    # Verify we can still parse frontmatter even if file is large
