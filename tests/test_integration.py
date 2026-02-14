"""Integration tests for end-to-end flow."""

from click.testing import CliRunner

from main import main


class TestIntegration:
    """Test suite for end-to-end integration."""

    def test_full_flow_generates_files(self, tmp_path):
        """Test complete flow generates both files correctly."""
        # Create a test project
        project_dir = tmp_path / "my-test-project"
        project_dir.mkdir()

        # Create README
        readme = project_dir / "README.md"
        readme.write_text(
            """# My Test Project

A complete test of the generator system.

## Features

- Automated documentation
- Git integration
- Configurable templates

## Technology

- Python 3.11
- Click for CLI
- PyYAML for config

## Getting Started

Install and run.
""",
            encoding="utf-8",
        )

        # Run the generator
        runner = CliRunner()
        result = runner.invoke(
            main,
            [str(project_dir), "--no-commit", "--verbose"],
            env={"PYTHONIOENCODING": "utf-8"},
        )

        # Check success
        assert (
            result.exit_code == 0
        ), f"Exit code {result.exit_code}.\nOutput:\n{result.output}\nException: {result.exception}"
        assert "Generated files" in result.output
        assert "Done!" in result.output

        # Check files exist in .clinerules/ directory
        rules_file = project_dir / ".clinerules" / "rules.md"
        skills_file = project_dir / ".clinerules" / "skills" / "index.md"

        assert rules_file.exists()
        assert skills_file.exists()

        # Check rules file content
        rules_content = rules_file.read_text(encoding="utf-8")
        assert "project: my-test-project" in rules_content
        assert "## DO" in rules_content
        # python should be detected from "Python 3.11"
        assert "python" in rules_content.lower()

        # Check skills file content
        skills_content = skills_file.read_text(encoding="utf-8")
        assert "project: my-test-project" in skills_content
        assert "## CORE SKILLS" in skills_content
        assert "cli-usability-auditor" in skills_content

    def test_flow_with_different_tech_stacks(self, tmp_path):
        """Test with various tech stack combinations."""
        test_cases = [
            {
                "name": "react-project",
                "tech": ["react", "typescript", "nextjs"],
                "tech_keys": ["react", "typescript"],
            },
            {
                "name": "ml-project",
                "tech": ["python", "pytorch", "fastapi"],
                "tech_keys": ["python", "pytorch"],
            },
            {
                "name": "infra-project",
                "tech": ["terraform", "aws", "docker", "kubernetes"],
                "tech_keys": ["terraform", "aws"],
            },
        ]

        runner = CliRunner()

        for case in test_cases:
            project_dir = tmp_path / case["name"]
            project_dir.mkdir()

            tech_list = "\n".join([f"- {t}" for t in case["tech"]])
            readme = project_dir / "README.md"
            readme.write_text(f"""# {case['name'].replace('-', ' ').title()}

Description.

## Tech

{tech_list}
""")

            result = runner.invoke(
                main,
                [str(project_dir), "--no-commit", "--quiet"],
                env={"PYTHONIOENCODING": "utf-8"},
            )
            assert result.exit_code == 0, f"Failed for {case['name']}"

            # Verify tech stack in output files
            rules = (project_dir / ".clinerules" / "rules.md").read_text(
                encoding="utf-8"
            )
            for tech in case["tech_keys"]:
                assert tech in rules, f"Expected {tech} in {case['name']} rules"

    def test_flow_preserves_existing_files(self, tmp_path):
        """Test that running twice updates files."""
        project_dir = tmp_path / "existing-project"
        project_dir.mkdir()

        readme = project_dir / "README.md"
        readme.write_text("# Existing Project\n\nDescription.")

        # First run
        runner = CliRunner()
        runner.invoke(
            main,
            [str(project_dir), "--no-commit", "--quiet"],
            env={"PYTHONIOENCODING": "utf-8"},
        )

        rules_file = project_dir / ".clinerules" / "rules.md"
        first_content = rules_file.read_text(encoding="utf-8")

        # Second run (should overwrite)
        runner.invoke(
            main,
            [str(project_dir), "--no-commit", "--quiet"],
            env={"PYTHONIOENCODING": "utf-8"},
        )

        second_content = rules_file.read_text(encoding="utf-8")

        # Files should exist and be similar
        assert rules_file.exists()
        assert "project: existing-project" in second_content

    def test_sample_project_integration(self, sample_project_path):
        """Test with the bundled sample project."""
        runner = CliRunner()

        # Clean up previously generated output for fresh test
        import shutil

        clinerules_dir = sample_project_path / ".clinerules"
        if clinerules_dir.exists():
            shutil.rmtree(clinerules_dir)

        result = runner.invoke(
            main,
            [str(sample_project_path), "--no-commit"],
            env={"PYTHONIOENCODING": "utf-8"},
        )

        assert result.exit_code == 0

        # Verify generated files in .clinerules/ directory
        rules = sample_project_path / ".clinerules" / "rules.md"
        skills = sample_project_path / ".clinerules" / "skills" / "index.md"

        assert rules.exists()
        assert skills.exists()

        # Verify content quality
        rules_content = rules.read_text(encoding="utf-8")
        assert "## DO" in rules_content
        assert "## DON'T" in rules_content or "DON'T" in rules_content
        assert "## PRIORITIES" in rules_content
        assert "## WORKFLOWS" in rules_content
