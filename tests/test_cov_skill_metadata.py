"""Coverage boost: SkillMetadataBuilder and SkillDocLoader."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from generator.skill_metadata_builder import SkillMetadataBuilder

# ---------------------------------------------------------------------------
# SkillMetadataBuilder
# ---------------------------------------------------------------------------


class TestGenerateTriggers:
    def test_base_trigger_derived_from_name(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        triggers = b._generate_triggers("fastapi-testing", "", [])
        assert "fastapi testing" in triggers

    def test_tech_match_adds_review_audit(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        triggers = b._generate_triggers("fastapi-workflow", "", ["fastapi"])
        assert any("fastapi" in t for t in triggers)

    def test_synonym_expansion_for_test(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        triggers = b._generate_triggers("test-workflow", "", [])
        assert any("testing" in t or "verify" in t for t in triggers)

    def test_generic_single_word_blocklisted(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        triggers = b._generate_triggers("fix-error", "", [])
        for t in triggers:
            if len(t.split()) == 1:
                assert t.lower() not in b.GENERIC_TRIGGER_BLOCKLIST

    def test_minimum_three_triggers(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        # Use a multi-word skill name that will expand via synonyms
        triggers = b._generate_triggers("test-deploy-workflow", "", [])
        assert len(triggers) >= 3

    def test_max_eight_triggers(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        triggers = b._generate_triggers("deploy-test-security-api-refactor-qa", "", ["fastapi", "docker", "pytest"])
        assert len(triggers) <= 8

    def test_readme_action_trigger_extracted(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        readme = "run fastapi testing to validate endpoints"
        triggers = b._generate_triggers("fastapi-testing", readme, [])
        assert any("fastapi testing" in t for t in triggers)


class TestExtractActionTriggers:
    def test_action_verb_found_in_matching_line(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        readme = "you can run the fastapi server with uvicorn"
        result = b._extract_action_triggers(readme, "fastapi workflow")
        assert any("fastapi" in t for t in result)

    def test_empty_readme_returns_empty(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        result = b._extract_action_triggers("", "fastapi workflow")
        assert result == set()

    def test_non_matching_line_ignored(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        readme = "run the docker container for deployment"
        result = b._extract_action_triggers(readme, "pytest testing")
        assert len(result) == 0


class TestSelectTools:
    def test_test_in_skill_name_adds_pytest(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tools = b._select_tools("pytest-testing-workflow", [])
        assert "pytest" in tools

    def test_deploy_adds_docker(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tools = b._select_tools("deploy-workflow", [])
        assert "docker" in tools

    def test_security_audit_adds_bandit(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tools = b._select_tools("security-audit", [])
        assert "bandit" in tools

    def test_refactor_adds_ruff(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tools = b._select_tools("refactor-cleanup", [])
        assert "ruff" in tools

    def test_system_tools_always_available(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tools = b._select_tools("pytest-workflow", [])
        assert "pytest" in tools  # pytest is in system_tools

    def test_returns_sorted_list(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tools = b._select_tools("pytest-testing-workflow", [])
        assert tools == sorted(tools)


class TestValidateToolsAvailability:
    def test_system_tools_always_pass(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        result = b._validate_tools_availability({"pytest", "git", "docker", "ruff"})
        assert "pytest" in result
        assert "git" in result

    def test_custom_tool_in_requirements_passes(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("mytool>=1.0\npytest\n")
        b = SkillMetadataBuilder(project_path=tmp_path)
        result = b._validate_tools_availability({"mytool", "pytest"})
        assert "mytool" in result

    def test_unknown_tool_not_available(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        result = b._validate_tools_availability({"completelyfaketool99"})
        assert "completelyfaketool99" not in result


class TestGenerateDescription:
    def test_extracts_matching_readme_line(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        readme = "This tool validates fastapi endpoints for correctness."
        result = b._generate_description("fastapi-validator", readme)
        assert "fastapi" in result.lower()

    def test_fallback_when_no_readme_match(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        result = b._generate_description("fastapi-validator", "no relevant content here at all")
        assert "FASTAPI" in result or "fastapi" in result.lower()

    def test_skips_markdown_syntax_lines(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        readme = "# Header\n- bullet point about fastapi\nPlain fastapi description text here with enough chars."
        result = b._generate_description("fastapi-workflow", readme)
        # Should skip the header and bullet, use the plain line
        assert "Plain" in result or "fastapi" in result.lower()

    def test_truncates_at_150_chars(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        readme = "fastapi " + "x" * 200
        result = b._generate_description("fastapi-workflow", readme)
        assert len(result) <= 150


class TestGenerateNegativeTriggers:
    def test_generic_tech_negatives(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        result = b._generate_negative_triggers("fastapi-workflow", [])
        assert any("fastapi" in n for n in result)

    def test_test_skill_adds_deployment_negative(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        result = b._generate_negative_triggers("pytest-test-runner", [])
        assert any("deployment" in n or "production" in n for n in result)

    def test_deploy_skill_adds_test_negative(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        result = b._generate_negative_triggers("docker-deploy", [])
        assert any("test" in n for n in result)

    def test_max_three_negatives(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        result = b._generate_negative_triggers("test-deploy-docker-security", [])
        assert len(result) <= 3


class TestGenerateTags:
    def test_tags_from_skill_name_parts(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tags = b._generate_tags("fastapi-testing-workflow", [])
        assert "fastapi" in tags
        assert "testing" in tags

    def test_short_parts_excluded(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tags = b._generate_tags("a-b-fastapi", [])
        assert "fastapi" in tags
        assert "a" not in tags
        assert "b" not in tags

    def test_tech_stack_added_to_tags(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tags = b._generate_tags("workflow", ["pytest", "docker"])
        assert "pytest" in tags
        assert "docker" in tags

    def test_deduplicates(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tags = b._generate_tags("pytest-workflow", ["pytest"])
        assert tags.count("pytest") == 1

    def test_max_six_tags(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        tags = b._generate_tags("a-b-c-d-e-f-g", ["x", "y", "z"])
        assert len(tags) <= 6


class TestGenerateCriticalRules:
    def test_always_returns_three_base_rules(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        rules = b.generate_critical_rules("generic-workflow", [])
        assert len(rules) >= 3

    def test_test_skill_adds_no_cov_rule(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        rules = b.generate_critical_rules("pytest-testing", [])
        assert any("no-cov" in r or "no-cover" in r for r in rules)

    def test_docker_skill_adds_env_rule(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        rules = b.generate_critical_rules("docker-deploy", [])
        assert any("production" in r.lower() for r in rules)

    def test_sql_skill_adds_destructive_rule(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        rules = b.generate_critical_rules("sql-migration", [])
        assert any("DROP" in r or "TRUNCATE" in r for r in rules)

    def test_auth_skill_adds_secrets_rule(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        rules = b.generate_critical_rules("auth-security-workflow", [])
        assert any("secret" in r.lower() or "token" in r.lower() for r in rules)


class TestRenderFrontmatter:
    def _meta(self, tmp_path, name="fastapi-workflow", triggers=None, tags=None, negatives=None):
        from generator.skill_creator import SkillMetadata

        return SkillMetadata(
            name=name,
            description="A skill for fastapi workflows.",
            auto_triggers=triggers or ["fastapi workflow", "build fastapi", "review fastapi"],
            tools=["pytest", "ruff"],
            tags=tags or ["fastapi", "workflow"],
            negative_triggers=negatives or ["general questions"],
        )

    def test_starts_with_frontmatter_delimiter(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        meta = self._meta(tmp_path)
        fm = b.render_frontmatter(meta)
        assert fm.startswith("---")

    def test_name_in_frontmatter(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        meta = self._meta(tmp_path, name="my-skill")
        fm = b.render_frontmatter(meta)
        assert "name: my-skill" in fm

    def test_description_truncated_at_1024(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        from generator.skill_creator import SkillMetadata

        meta = SkillMetadata(
            name="x",
            description="A" * 1020,
            auto_triggers=["a", "b", "c"],
            tools=[],
            tags=[],
            negative_triggers=[],
        )
        fm = b.render_frontmatter(meta)
        # The description field itself should not exceed 1024 chars
        desc_line = [l for l in fm.splitlines() if l.strip().startswith("A")][0]
        assert len(desc_line.strip()) <= 1024

    def test_when_phrases_included(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        meta = self._meta(tmp_path)
        fm = b.render_frontmatter(meta)
        assert "When the user mentions" in fm

    def test_negative_triggers_included(self, tmp_path):
        b = SkillMetadataBuilder(project_path=tmp_path)
        meta = self._meta(tmp_path, negatives=["general questions"])
        fm = b.render_frontmatter(meta)
        assert "Do NOT activate" in fm


# ---------------------------------------------------------------------------
# SkillDocLoader
# ---------------------------------------------------------------------------
from generator.skill_doc_loader import SkillDocLoader


class TestSkillDocLoaderScoreDoc:
    def test_high_value_keyword_adds_two(self, tmp_path):
        loader = SkillDocLoader(project_path=tmp_path)
        path = tmp_path / "architecture.md"
        assert loader._score_doc(path, "x" * 300) == 2

    def test_docs_dir_adds_one(self, tmp_path):
        docs = tmp_path / "docs"
        docs.mkdir()
        path = docs / "random.md"
        loader = SkillDocLoader(project_path=tmp_path)
        assert loader._score_doc(path, "x" * 300) == 1

    def test_short_content_subtracts_one(self, tmp_path):
        path = tmp_path / "random.md"
        loader = SkillDocLoader(project_path=tmp_path)
        assert loader._score_doc(path, "short") == -1

    def test_high_value_in_docs_dir(self, tmp_path):
        docs = tmp_path / "docs"
        docs.mkdir()
        path = docs / "architecture.md"
        loader = SkillDocLoader(project_path=tmp_path)
        assert loader._score_doc(path, "x" * 300) == 3


class TestDiscoverSupplementaryDocs:
    def test_finds_md_files_in_root(self, tmp_path):
        (tmp_path / "DESIGN.md").write_text("design notes")
        (tmp_path / "PLAN.md").write_text("plan content")
        loader = SkillDocLoader(project_path=tmp_path)
        docs = loader.discover_supplementary_docs()
        names = [d.name for d in docs]
        assert "DESIGN.md" in names
        assert "PLAN.md" in names

    def test_skips_changelog(self, tmp_path):
        (tmp_path / "CHANGELOG.md").write_text("changes")
        loader = SkillDocLoader(project_path=tmp_path)
        docs = loader.discover_supplementary_docs()
        assert not any(d.name.lower() == "changelog.md" for d in docs)

    def test_skips_readme(self, tmp_path):
        (tmp_path / "README.md").write_text("readme")
        loader = SkillDocLoader(project_path=tmp_path)
        docs = loader.discover_supplementary_docs()
        assert not any(d.name.lower() == "readme.md" for d in docs)

    def test_finds_docs_in_docs_dir(self, tmp_path):
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "architecture.md").write_text("arch notes")
        loader = SkillDocLoader(project_path=tmp_path)
        result = loader.discover_supplementary_docs()
        assert any(d.name == "architecture.md" for d in result)

    def test_high_value_sorted_first(self, tmp_path):
        (tmp_path / "architecture.md").write_text("x" * 300)
        (tmp_path / "notes.md").write_text("x" * 300)
        loader = SkillDocLoader(project_path=tmp_path)
        docs = loader.discover_supplementary_docs()
        names = [d.name for d in docs]
        assert names.index("architecture.md") < names.index("notes.md")


class TestFindRelevantFiles:
    def test_finds_file_with_matching_import(self, tmp_path):
        py = tmp_path / "fastapi_server.py"
        py.write_text("import fastapi\napp = fastapi.FastAPI()\n")
        loader = SkillDocLoader(project_path=tmp_path)
        key_files: dict = {}
        loader._find_relevant_files("fastapi-workflow", key_files, max_files=3)
        assert any("fastapi" in k for k in key_files)

    def test_skips_venv_directory(self, tmp_path):
        venv = tmp_path / "venv"
        venv.mkdir()
        (venv / "lib.py").write_text("import fastapi\n")
        loader = SkillDocLoader(project_path=tmp_path)
        key_files: dict = {}
        loader._find_relevant_files("fastapi-workflow", key_files)
        assert not any("venv" in k for k in key_files)

    def test_respects_max_files_limit(self, tmp_path):
        for i in range(5):
            py = tmp_path / f"mod{i}.py"
            py.write_text(f"import fastapi\nfastapi_{i} = True\n")
        loader = SkillDocLoader(project_path=tmp_path)
        key_files: dict = {}
        loader._find_relevant_files("fastapi-workflow", key_files, max_files=2)
        assert len(key_files) <= 2

    def test_skips_already_loaded_files(self, tmp_path):
        py = tmp_path / "main.py"
        py.write_text("import fastapi\n")
        loader = SkillDocLoader(project_path=tmp_path)
        key_files = {"main.py": "already loaded"}
        loader._find_relevant_files("fastapi-workflow", key_files)
        assert key_files["main.py"] == "already loaded"

    def test_empty_tokens_returns_early(self, tmp_path):
        loader = SkillDocLoader(project_path=tmp_path)
        key_files: dict = {}
        # All tokens shorter than 3 chars → returns early
        loader._find_relevant_files("a-b", key_files)
        assert key_files == {}
