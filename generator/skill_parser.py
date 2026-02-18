import json
import re
from pathlib import Path
from typing import Dict, List

from generator.utils.tech_detector import extract_context as _extract_context


class SkillParser:
    """Handles parsing of skill content and README context."""

    @staticmethod
    def clean_markdown(text: str) -> str:
        """Strip markdown formatting from a line."""
        s = text.strip()
        # Remove leading list markers and arrows
        s = re.sub(r"^[-*→>]\s*", "", s)
        s = re.sub(r"^→+\s*", "", s)
        # Remove bold/italic markers
        s = s.replace("**", "").replace("*", "")
        # Remove link syntax [text](url) → text
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        # Remove badge images ![alt](url)
        s = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", s)
        # Remove inline code backticks (keep content)
        s = s.replace("`", "")
        # Collapse multiple spaces
        s = re.sub(r"\s{2,}", " ", s).strip()
        return s

    @staticmethod
    def extract_tech_context(tech: str, readme_content: str) -> List[str]:
        """Extract lines from README that mention a specific technology.
        
        Delegates to generator.utils.tech_detector.extract_context().
        Kept for backward compatibility.
        """
        return _extract_context(tech, readme_content)

    @staticmethod
    def summarize_purpose(
        tech: str, context_lines: List[str], project_name: str
    ) -> str:
        """Build a purpose statement from extracted context."""
        if not context_lines:
            return (
                f"Integration patterns for {tech} in {project_name or 'this project'}."
            )

        # Find the most descriptive line — skip commands, tables, arrows-only
        best = ""
        for line in context_lines:
            clean = SkillParser.clean_markdown(line)
            # Skip non-descriptive lines
            if (
                clean.startswith("#")
                or clean.startswith("|")
                or clean.startswith("pip ")
                or clean.startswith("npm ")
                or clean.startswith("uvicorn ")
                or clean.startswith("docker ")
                or len(clean) < 10
            ):
                continue
            # Prefer lines that look like prose (has spaces, no excessive arrows)
            arrow_count = clean.count("→") + clean.count("->")
            if arrow_count > 2:
                continue
            if len(clean) > len(best):
                best = clean

        if best:
            return f"How {project_name or 'this project'} uses {tech}: {best}"
        return f"Integration patterns for {tech} in {project_name or 'this project'}."

    @staticmethod
    def build_triggers(tech: str, context_lines: List[str]) -> str:
        """Build auto-trigger rules from context."""
        triggers = []

        # Extract file types and patterns mentioned in context
        for line in context_lines:
            # Look for file references
            files = re.findall(r"(\w+\.(?:py|js|ts|jsx|tsx|yaml|yml|json|toml))", line)
            for f in files:
                trigger = f"- Editing or creating `{f}`"
                if trigger not in triggers:
                    triggers.append(trigger)

            # Look for command/import patterns
            imports = re.findall(r"(?:import|from)\s+(\w+)", line)
            for imp in imports:
                if imp.lower() in tech.lower() or tech.lower() in imp.lower():
                    trigger = f"- Files importing `{imp}`"
                    if trigger not in triggers:
                        triggers.append(trigger)

        # Always add the base trigger
        triggers.append(f"- Working with {tech} integration code")
        triggers.append(f"- Editing files that import or configure {tech}")

        return "\n".join(triggers)

    @staticmethod
    def build_guidelines(tech: str, context_lines: List[str]) -> str:
        """Build guidelines from extracted project context."""
        guidelines = []

        for line in context_lines:
            clean = SkillParser.clean_markdown(line)
            # Skip non-actionable lines
            if (
                not clean
                or clean.startswith("#")
                or clean.startswith("|")
                or len(clean) < 10
            ):
                continue
            # Skip raw shell commands
            if re.match(
                r"^(pip |npm |yarn |uvicorn |docker |git clone|cd |mkdir )", clean
            ):
                continue
            # Skip lines that are mostly arrows/diagrams
            if clean.count("→") + clean.count("->") > 2:
                continue

            # Lines describing architecture, config, or usage are useful
            if ":" in clean and len(clean) < 200:
                guidelines.append(f"- {clean}")
            elif re.search(
                r"(model|endpoint|config|api|key|token|port|host|stream|async|route|setup)",
                clean,
                re.I,
            ):
                guidelines.append(f"- {clean}")

        if not guidelines:
            guidelines.append(f"- Follow project patterns for {tech} usage")

        guidelines.append(f"- Handle {tech} errors with proper retries and fallbacks")
        guidelines.append(f"- Add tests for {tech} integration code")

        return "\n".join(guidelines[:8])

    @staticmethod
    def extract_all_triggers(
        all_skills_content: Dict[str, Dict],
    ) -> Dict[str, List[str]]:
        """
        Extract auto-trigger phrases from all skills (Project > Learned > Builtin).
        Returns: { 'skill_name': ['phrase 1', 'phrase 2'] }
        """
        triggers = {}

        # We iterate in reverse priority so higher priority overwrites lower if names collide
        for category in ["builtin", "learned", "project"]:
            if category not in all_skills_content:
                continue

            for skill_name, skill_data in all_skills_content[category].items():
                content = skill_data["content"]

                # Match "## Auto-Trigger" section
                match = re.search(
                    r"## Auto-Trigger\n(.*?)(?:\n## |\Z)", content, re.DOTALL
                )
                if match:
                    trigger_text = match.group(1)
                    conditions = []
                    for line in trigger_text.split("\n"):
                        line = line.strip()
                        if not line.startswith("-"):
                            continue

                        # Clean line
                        clean_line = line.strip("- ").strip().lower()

                        # improved parsing: extract phrases in quotes
                        quoted_phrases = re.findall(r'"([^"]*)"', clean_line)
                        if quoted_phrases:
                            conditions.extend(quoted_phrases)
                        else:
                            # If no quotes, use the whole line but remove common prefixes
                            for prefix in [
                                "user says:",
                                "user reports:",
                                "when ",
                                "before ",
                                "after ",
                            ]:
                                if clean_line.startswith(prefix):
                                    clean_line = clean_line[len(prefix) :].strip()
                            conditions.append(clean_line)

                    if conditions:
                        triggers[skill_name] = conditions

        return triggers

    @staticmethod
    def save_triggers_json(triggers: Dict[str, List[str]], output_dir: Path):
        """Save extracted triggers to .clinerules/auto-triggers.json"""
        output_file = output_dir / "auto-triggers.json"

        try:
            output_file.write_text(json.dumps(triggers, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Warning] Failed to save auto-triggers.json: {e}")

    @staticmethod
    def parse_skill_md(content: str, filename: str) -> Dict:
        """
        Parse a skill markdown file to extract structured components.
        Returns a dict with: name, description, triggers, when_to_use, tools, command, io
        """
        parsed = {
            "name": filename.replace(".md", ""),
            "description": "",
            "triggers": [],
            "when_to_use": "",
            "tools": ["read", "exec"],  # Safe default
            "command": "",
            "input_output": "",
        }
        
        lines = content.split("\n")
        
        # 1. Extract Description (First non-header paragraph)
        for line in lines:
            clean = line.strip()
            if not clean or clean.startswith("#") or clean.startswith("---") or clean.startswith(">"):
                continue
            parsed["description"] = clean
            break
            
        # 2. Extract Sections using Regex for robustness
        # Triggers
        triggers_match = re.search(r"##\s+Triggers\s*\n(.*?)(?:\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
        if triggers_match:
            raw_triggers = triggers_match.group(1).strip()
            # Parse list items
            parsed["triggers"] = [
                line.strip("- *").strip() 
                for line in raw_triggers.split("\n") 
                if line.strip().startswith("-") or line.strip().startswith("*")
            ]
        
        # When to Use
        when_match = re.search(r"##\s+When to use\s*\n(.*?)(?:\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
        if when_match:
            parsed["when_to_use"] = when_match.group(1).strip()
            
        # Tools
        tools_match = re.search(r"##\s+Tools\s*\n(.*?)(?:\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
        if tools_match:
            raw_tools = tools_match.group(1).strip()
            # Extract tools if commas or newlines
            tools_list = re.findall(r"\b\w+\b", raw_tools)
            if tools_list:
                parsed["tools"] = tools_list
                
        # Command / Usage
        usage_match = re.search(r"##\s+(?:Command|Usage)\s*\n(.*?)(?:\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
        if usage_match:
            parsed["command"] = usage_match.group(1).strip()
            
        # Input / Output
        io_match = re.search(r"##\s+(?:Input/Output|I/O)\s*\n(.*?)(?:\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
        if io_match:
            parsed["input_output"] = io_match.group(1).strip()
        else:
            # Fallback: check separate Input and Output sections
            input_match = re.search(r"##\s+Input\s*\n(.*?)(?:\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
            output_match = re.search(r"##\s+Output\s*\n(.*?)(?:\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
            parts = []
            if input_match:
                parts.append(f"Input: {input_match.group(1).strip()}")
            if output_match:
                parts.append(f"Output: {output_match.group(1).strip()}")
            if parts:
                parsed["input_output"] = " / ".join(parts)

        # 3. Smart Defaults (Fill gaps)
        if not parsed["triggers"] and parsed["when_to_use"]:
            # Infer triggers from 'When to use' bullets
            parsed["triggers"] = [
                line.strip("- *").strip().lower()
                for line in parsed["when_to_use"].split("\n")
                if line.strip().startswith("-")
            ]
            
        if not parsed["command"]:
            # Default command pattern
            parsed["command"] = f"`prg {parsed['name']}`"
            
        if not parsed["input_output"]:
            parsed["input_output"] = "Standard CLI I/O"
            
        return parsed
