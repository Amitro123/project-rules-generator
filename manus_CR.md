Code Review: Amitro123/project-rules-generator

Date: 2026-03-10
Reviewer: Manus AI

1. Executive Summary

The project-rules-generator is a well-architected and ambitious project aiming to automate the creation of contextual, intelligent rules and skills for AI agents. Its core strength lies in its modular design, featuring a layered skill resolution system and an extensible strategy pattern for skill generation. The project successfully demonstrates the ability to parse a project's README.md and generate a basic SKILL.md file.

However, the review identifies several key areas for improvement. The installation process has minor dependency and packaging issues that hinder initial setup. More significantly, the intelligence of the skill generation can be enhanced. The system currently misses opportunities to extract detailed, actionable steps and anti-patterns from project documentation, often defaulting to generic templates. This review provides specific, actionable recommendations to address these points, which would substantially elevate the quality and utility of the generated skills.

2. Installation and Setup

The initial setup process encountered a few obstacles that required manual intervention. A smooth first-time user experience is critical, and addressing these issues should be a high priority.

File
Issue
Recommendation
pyproject.toml
The packages list in the [tool.setuptools] section incorrectly included "analyzer" and "src", which are non-existent directories, causing the pip install -e . command to fail.
Correct the packages list to include the actual package directories: packages = ["generator", "prg_utils", "cli"].
pyproject.toml
The project depends on the python-dotenv package to load environment variables in cli/cli.py, but this dependency is not listed in pyproject.toml. This results in a ModuleNotFoundError at runtime.
Add "python-dotenv" to the dependencies list in pyproject.toml to ensure all required packages are installed automatically.




3. Skill Generation Mechanism: A Deep Dive

The skills mechanism is the core of this project. I tested it by creating a simple dummy project with a README.md and then running the skill creation command. This process revealed both the strengths and weaknesses of the current implementation.

3.1. The Test Case

A dummy project named Super Calculator was created with the following README.md:

Markdown


# Super Calculator

A simple calculator project.

## Features
- Addition
- Subtraction

## Development Workflow
To add a new operation:
1. Create a new file in `ops/`
2. Implement the `calculate` function
3. Add tests in `tests/`
4. Run `pytest` to verify

## Coding Standards
- Always use type hints
- Never use global variables
- Use `decimal` for financial calculations



The command prg analyze . --create-skill "operation-adder" --from-readme README.md was executed. It successfully generated a SKILL.md file, but the content was largely generic.

3.2. Analysis of Generated Skill

The generated skill was a mix of accurately extracted high-level information and missed details.

•
Purpose Extraction: The system correctly identified the project's purpose ("A simple calculator project") from the README.md.

•
Process Extraction: This was a major weakness. The generated Process section contained only generic placeholders ("Verify changes are correct and tests pass."). It completely missed the explicit, step-by-step Development Workflow outlined in the README.md. The extract_process_steps function in generator/analyzers/readme_parser.py appears to be too narrowly focused on "quick start" or "installation" sections and fails to parse more general workflow descriptions.

•
Anti-Pattern Extraction: The Anti-Patterns section was empty. The system did not identify the rules in the Coding Standards section (e.g., "Never use global variables") as potential anti-patterns. The extract_anti_patterns function seems to rely on explicit ❌ markers or pre-defined structural checks, which limits its flexibility.

•
Trigger Generation: The auto-triggers were derived solely from the skill's name ("operation", "adder"). More intelligent triggers could have been inferred from the workflow, such as "add a new operation" or "create a calculate function".

4. Code-Level Feedback and Recommendations

File
Function/Area
Feedback & Recommendation
generator/analyzers/readme_parser.py
extract_process_steps
Issue: The function is too specific to installation sections. Recommendation: Generalize this function to look for headers like "Workflow", "Development Process", or "How to Contribute". It should be able to parse both numbered and bulleted lists under these sections to capture the core operational steps of a project.
generator/analyzers/readme_parser.py
extract_anti_patterns
Issue: The function is not capturing rules from sections like "Coding Standards". Recommendation: Enhance the function to search for sections titled "Coding Standards", "Best Practices", or "Rules". Within these sections, it should identify imperative statements, especially negative ones (e.g., "Never...", "Do not..."), and convert them into anti-patterns.
generator/strategies/readme_strategy.py
generate
Issue: The strategy relies on the parser but doesn't seem to effectively assemble the parsed components into a high-quality skill. Recommendation: After improving the parser, ensure this strategy method populates the Process and Anti-Patterns sections of the skill template with the newly extracted, detailed information instead of generic placeholders.
generator/llm_skill_generator.py
_build_prompt
Issue: The prompt for the LLM is generic. Recommendation: Make the prompt more dynamic. Include the specifically extracted Process steps and Anti-Patterns as few-shot examples or explicit instructions within the prompt. This will guide the LLM to generate content that is highly specific and faithful to the project's documented conventions.
generator/skill_discovery.py
_link_or_copy
Issue: The method uses print for warnings. Recommendation: Replace the print statement with the standard logging module for consistency and better control over log levels and output streams.




5. Conclusion

project-rules-generator is a powerful concept with a solid architectural foundation. By addressing the installation friction and, most importantly, by significantly improving the intelligence of the README.md parsing and skill generation strategies, this project can evolve from a promising tool into an indispensable utility for AI agent development. The recommendations outlined in this review provide a clear path toward achieving that goal.

