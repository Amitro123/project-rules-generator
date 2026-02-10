from pathlib import Path
from typing import List, Dict, Optional
import re

class SkillsManager:
    """Manages skill discovery, creation, and loading."""

    def __init__(self, base_path: Optional[Path] = None, learned_path: Optional[Path] = None):
        # Default to current directory (src/skills)
        if base_path is None:
            self.base_path = Path(__file__).parent
        else:
            self.base_path = base_path

        self.builtin_path = self.base_path / "builtin"

        # storage for learned skills (project dir or user directory)
        if learned_path is not None:
            self.learned_path = Path(learned_path)
        else:
            self.learned_path = Path.home() / ".project-rules-generator" / "learned_skills"

    def list_skills(self) -> Dict[str, List[str]]:
        """List all available skills organized by category."""
        skills = {
            "builtin": [],
            "learned": []
        }

        for category, path in [("builtin", self.builtin_path), ("learned", self.learned_path)]:
            if path.exists():
                skills[category] = sorted(self._scan_directory(path))

        return skills

    def _scan_directory(self, path: Path, prefix: str = "") -> List[str]:
        """Recursively scan for skills (YAML or SKILL.md)."""
        found = []
        try:
            for item in path.iterdir():
                # Case 1: YAML definition (e.g. skill.yaml)
                if item.is_file() and item.suffix in ['.yaml', '.yml']:
                     found.append(f"{prefix}{item.stem}")
                
                # Case 2: Directory with SKILL.md (legacy/rich)
                elif item.is_dir():
                    if (item / "SKILL.md").exists():
                        found.append(f"{prefix}{item.name}")
                    
                    # Recurse
                    # Only recurse if we didn't just match a skill (skills are leaves)
                    # changing logic slightly: allow nested categories
                    found.extend(self._scan_directory(item, prefix=f"{prefix}{item.name}/"))
        except PermissionError:
            pass
        return found

    def create_skill(self, name: str, from_readme: Optional[str] = None, project_path: Optional[str] = None, use_ai: bool = False) -> Path:
        """Create a new learned skill."""
        # Sanitize name
        safe_name = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))
        if not safe_name:
            raise ValueError("Invalid skill name provided.")

        target_dir = self.learned_path / safe_name
        if target_dir.exists():
            raise FileExistsError(f"Skill '{safe_name}' already exists.")

        target_dir.mkdir(parents=True, exist_ok=True)
        skill_file = target_dir / "SKILL.md"

        content = ""
        
        # 1. AI Generation
        if use_ai and project_path:
            try:
                from generator.project_analyzer import ProjectAnalyzer
                from generator.llm_skill_generator import LLMSkillGenerator
                
                print(f"🤖 Analyzing project context in {project_path}...")
                analyzer = ProjectAnalyzer(Path(project_path))
                context = analyzer.analyze()

                print("✨ Generating skill with AI...")
                generator = LLMSkillGenerator()
                content = generator.generate_skill(safe_name, context)
            except Exception as e:
                print(f"[!] Warning: AI generation failed ({e}). Falling back to standard parsing.")
                # Fallthrough

        # 2. Smart README Parsing (if AI didn't generate content)
        if not content and from_readme:
            readme_path = Path(from_readme)
            if readme_path.exists():
                try:
                    from analyzer.readme_parser import (
                        extract_purpose, extract_tech_stack, 
                        extract_auto_triggers, extract_process_steps, 
                        extract_anti_patterns
                    )
                    
                    readme_content = readme_path.read_text(encoding='utf-8', errors='replace')
                    
                    purpose = extract_purpose(readme_content)
                    tech = extract_tech_stack(readme_content)
                    triggers = extract_auto_triggers(readme_content, safe_name)
                    steps = extract_process_steps(readme_content)
                    anti_patterns = extract_anti_patterns(readme_content, tech, project_path=readme_path.parent)
                    
                    # Build skill content
                    title = safe_name.replace('-', ' ').title()
                    content = f"# Skill: {title}\n\n"
                    content += f"## Purpose\n{purpose}\n\n"
                    
                    content += "## Auto-Trigger\n"
                    content += "\n".join(['- ' + t for t in triggers]) + "\n\n"
                    
                    content += "## Process\n\n"
                    step_count = 1
                    for step in steps:
                        if step.strip().startswith('```'):
                            content += f"{step}\n\n"
                        else:
                            # Clean existing numbering
                            clean_step = re.sub(r'^\d+\.\s*', '', step)
                            content += f"### {step_count}. {clean_step}\n\n"
                            step_count += 1
                            
                    content += "## Output\n[Describe what artifacts or state changes result from following this skill]\n\n"
                    
                    content += "## Anti-Patterns\n"
                    for ap in anti_patterns:
                        content += f"❌ {ap}\n"
                        
                    if tech:
                        content += f"\n## Tech Stack\n{', '.join(tech)}\n"
                        
                    content += f"\n## Context (from {readme_path.name})\n\n{readme_content}\n"

                except Exception as e:
                    print(f"[!] Warning: Smart parsing failed ({e}). Falling back to template.")
                    # Fallthrough to template + context
                    pass
            else:
                 print(f"[!] Warning: README {from_readme} not found.")

        # 3. Fallback / Default Template if content not generated
        if not content:
            if from_readme and Path(from_readme).exists():
                 # Valid readme but parsing failed or was skipped
                 readme_path = Path(from_readme)
                 readme_content = readme_path.read_text(encoding='utf-8', errors='replace')
                 additional_context = f"\n\n## Context (from {readme_path.name})\n\n{readme_content}\n"
            else:
                 additional_context = ""

            title = safe_name.replace('-', ' ').title()
            content = f"""# Skill: {title}

## Purpose
[One sentence: what problem does this solve]

## Auto-Trigger
[When should agent activate this skill]

## Process
[Step-by-step instructions]

## Output
[What artifact/state results]

## Anti-Patterns
[x] [What NOT to do]
"""
            content += additional_context

        skill_file.write_text(content, encoding='utf-8')
        return target_dir

    def get_all_skills_content(self) -> Dict[str, Dict]:
        """Get full content of all skills for export."""
        skills_content = {
            'builtin': {},
            'learned': {}
        }
        
        # Helper to read skills
        def _read_skills(path: Path, category: str):
            if not path.exists():
                return
            skills_list = self._scan_directory(path)
            for skill_rel_path in skills_list:
                # Skill list returns relative paths like 'category/skill'
                # Check for YAML first
                
                # We need to resolve the actual file from the relative path returned by scan
                # "category/skill" could be "path/category/skill.yaml" or "path/category/skill/SKILL.md"
                
                # Re-construct lookup (simplistic)
                # This part is tricky because _scan_directory returns flattened names but we need file paths
                
                # Let's try locating it again relative to base path
                # A better approach for scan might be returning tuples (name, path)
                # For now, let's look for both candidates
                
                # Check 1: YAML
                yaml_path = path / f"{skill_rel_path}.yaml"
                yml_path = path / f"{skill_rel_path}.yml"
                md_path = path / skill_rel_path / "SKILL.md"
                
                skill_file = None
                if yaml_path.exists(): skill_file = yaml_path
                elif yml_path.exists(): skill_file = yml_path
                elif md_path.exists(): skill_file = md_path
                
                if skill_file:
                    content = skill_file.read_text(encoding='utf-8', errors='replace')
                    
                    skill_name = skill_rel_path.split('/')[-1] # Leaf name
                    skills_content[category][skill_name] = {
                        'path': str(skill_file),
                        'content': content
                    }

        _read_skills(self.builtin_path, 'builtin')
        _read_skills(self.learned_path, 'learned')
        
        return skills_content

    def extract_auto_triggers(self) -> List[Dict]:
        """Extract auto-trigger rules from all skills."""
        triggers = []
        
        all_skills = self.get_all_skills_content()
        # Only use builtin and learned (awesome removed!)
        for category in ['builtin', 'learned']:
            if category not in all_skills:
                continue

            for skill_name, skill_data in all_skills[category].items():
                content = skill_data['content']
                
                # Extract Auto-Trigger section
                # Match content between "## Auto-Trigger" and next "## " section or end of file
                match = re.search(r'## Auto-Trigger\n(.*?)(?:\n## |\Z)', content, re.DOTALL)
                if match:
                    trigger_text = match.group(1)
                    conditions = [
                        line.strip('- ').strip()
                        for line in trigger_text.split('\n')
                        if line.strip().startswith('-')
                    ]
                    
                    if conditions:
                        triggers.append({
                            'skill': skill_name,
                            'category': category,
                            'conditions': conditions
                        })
        
        return triggers
