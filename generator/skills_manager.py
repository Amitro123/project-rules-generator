from pathlib import Path
from typing import List, Dict, Optional
import re

class SkillsManager:
    """Manages skill discovery, creation, and loading."""

    def __init__(self, project_path: Optional[Path] = None):
        """
        Initialize SkillsManager with Global and Project layers.
        
        Layers:
        1. Project (.clinerules/skills/project) - Metric overrides
        2. Global Learned (~/.project-rules-generator/learned) - User's shared skills
        3. Global Builtin (~/.project-rules-generator/builtin) - Core PRG skills
        """
        self.project_path = Path(project_path) if project_path else None
        
        # 1. Global Cache Paths
        self.global_root = Path.home() / ".project-rules-generator"
        self.global_builtin = self.global_root / "builtin"
        self.global_learned = self.global_root / "learned"
        
        # 2. Package Source (for syncing builtin)
        self.package_builtin = Path(__file__).parent / "skills" / "builtin"
        
        # 3. Project Paths (if valid project)
        if self.project_path:
            self.project_skills_root = self.project_path / ".clinerules" / "skills"
            self.project_local_dir = self.project_skills_root / "project"
            self.project_learned_link = self.project_skills_root / "learned"
            self.project_builtin_link = self.project_skills_root / "builtin"
        else:
            self.project_skills_root = None
            self.project_local_dir = None

    def ensure_global_structure(self):
        """Ensure global cache directories exist and are synced."""
        self.global_root.mkdir(parents=True, exist_ok=True)
        self.global_learned.mkdir(parents=True, exist_ok=True)
        self.global_builtin.mkdir(parents=True, exist_ok=True)

        # Sync package builtin skills to global cache
        # This ensures the global cache always has the latest core skills
        if self.package_builtin.exists():
            import shutil
            # Simple sync: copy if newer/missing
            try:
                # We iterate package items and copy them to global
                for item in self.package_builtin.iterdir():
                    dest = self.global_builtin / item.name
                    if item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
            except Exception as e:
                # Non-critical, just warning
                print(f"[Warning] Failed to sync builtin skills to global cache: {e}")

    def setup_project_structure(self):
        """
        Create project .clinerules/skills structure with symlinks to global cache.
        Fallback to copying if symlinks fail (common on Windows).
        """
        if not self.project_skills_root:
            raise ValueError("Project path not set")

        self.ensure_global_structure()
        
        # 1. Create local overrides dir
        self.project_local_dir.mkdir(parents=True, exist_ok=True)

        # 2. Link/Copy Builtin & Learned
        self._link_or_copy(self.global_builtin, self.project_builtin_link)
        self._link_or_copy(self.global_learned, self.project_learned_link)

    def _link_or_copy(self, source: Path, target: Path):
        """Try to symlink, fallback to copy."""
        import shutil
        import os

        if target.exists():
            if target.is_symlink():
                # check if valid? for now assume yes or re-link
                 # If it points to wrong place, remove it
                try:
                    if target.resolve() != source.resolve():
                        target.unlink()
                    else:
                        return # Already correct
                except Exception:
                    # Resolve failed, probably broken
                    target.unlink()
            elif target.is_dir():
                 # It's a directory (maybe from fallback copy). 
                 # We leave it alone usually, BUT if we want to enforce symlinks we might remove?
                 # Strategy: If we requested a link, and it's a dir, maybe we should update it?
                 # For safety/speed, let's just assume if it exists it's fine, 
                 # unless user explicitly asked to force update (not implemented yet).
                 return 
        
        # Try symlink
        try:
            os.symlink(source, target, target_is_directory=True)
        except (OSError, AttributeError) as e:
            # Fallback to copy
            # Only copy if source exists
            if source.exists():
                try:
                    if source.is_dir():
                        shutil.copytree(source, target)
                    else:
                        # shouldn't happen for these main folders
                        pass
                except Exception as copy_err:
                     print(f"[Warning] Failed to link or copy {source} to {target}: {copy_err}")

    def list_skills(self) -> Dict[str, Dict[str, str]]:
        """
        List all available skills with their source resolution.
        Returns: { 'skill_name': {'type': 'builtin'|'learned'|'project', 'path': ...} }
        """
        self.ensure_global_structure()
        
        skills = {}

        # 1. Load Builtin (Lowest Priority)
        for s in self._scan_directory(self.global_builtin):
            name = s.split('/')[-1] # simplistic name extraction
            skills[name] = {'type': 'builtin', 'path': self.global_builtin / f"{s}.md"} # approx path

        # 2. Load Learned (Medium Priority)
        for s in self._scan_directory(self.global_learned):
            name = s.split('/')[-1]
            skills[name] = {'type': 'learned', 'path': self.global_learned / f"{s}.md"}

        # 3. Load Project (Highest Priority)
        if self.project_local_dir and self.project_local_dir.exists():
            for s in self._scan_directory(self.project_local_dir):
                name = s.split('/')[-1]
                skills[name] = {'type': 'project', 'path': self.project_local_dir / f"{s}.md"}
        
        return skills

    def resolve_skill(self, skill_name: str) -> Optional[Path]:
        """Find the active skill file based on priority."""
        # Check Project
        if self.project_local_dir:
            p_path = self.project_local_dir / f"{skill_name}.md"
            if p_path.exists(): return p_path
            
            # recursive/nested search if needed? keeping simple for now
        
        # Check Learned
        l_path = self.global_learned / f"{skill_name}.md"
        if l_path.exists(): return l_path
        
        l_subdir = self.global_learned / skill_name / "SKILL.md"
        if l_subdir.exists(): return l_subdir

        # Check Builtin
        b_path = self.global_builtin / f"{skill_name}.md"
        if b_path.exists(): return b_path
        
        # builtin might have categorization
        # Need smarter search? _scan_directory knows. 
        # But for resolving by name, we might need a lookup map if names are unique.
        # Assuming flat namespace for simplicity or "category/name" convention?
        # The prompt examples use "fastapi", "react".
        
        # Let's search deeply if not found
        for root in [self.global_learned, self.global_builtin]:
             found = list(root.rglob(f"{skill_name}.md"))
             if found: return found[0]
             found_dir = list(root.rglob(f"{skill_name}/SKILL.md"))
             if found_dir: return found_dir[0]

        return None

    def _scan_directory(self, path: Path, prefix: str = "") -> List[str]:
        """Recursively scan for skills (YAML or SKILL.md)."""
        found = []
        if not path.exists(): return found
        
        try:
            for item in path.iterdir():
                # Case 1: YAML definition (e.g. skill.yaml)
                if item.is_file() and item.suffix in ['.yaml', '.yml']:
                     found.append(f"{prefix}{item.stem}")
                elif item.is_file() and item.suffix == '.md':
                     found.append(f"{prefix}{item.stem}")
                
                # Case 2: Directory with SKILL.md (legacy/rich)
                elif item.is_dir():
                    if (item / "SKILL.md").exists():
                        found.append(f"{prefix}{item.name}")
                    else:
                        # Recurse
                        found.extend(self._scan_directory(item, prefix=f"{prefix}{item.name}/"))
        except PermissionError:
            pass
        return found

    def create_skill(self, name: str, from_readme: Optional[str] = None, project_path: Optional[str] = None, use_ai: bool = False) -> Path:
        """Create a new learned skill in the GLOBAL cache."""
        self.ensure_global_structure()
        
        # Sanitize name
        safe_name = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))
        if not safe_name:
            raise ValueError("Invalid skill name provided.")

        # Target is GLOBAL learned
        target_dir = self.global_learned / safe_name
        if target_dir.exists():
            print(f"Skill '{safe_name}' already exists in global learned cache. Updating...")
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            
        skill_file = target_dir / "SKILL.md"

        content = ""
        
        # 1. AI Generation
        if use_ai and project_path:
            try:
                from generator.project_analyzer import ProjectAnalyzer
                from generator.llm_skill_generator import LLMSkillGenerator
                # ... (rest of logic same, just using skill_file)
                pass # logic continues below...


                print(f"🤖 Analyzing project context in {project_path}...")
                analyzer = ProjectAnalyzer(Path(project_path))
                context = analyzer.analyze()

                print("✨ Generating skill with AI...")
                generator = LLMSkillGenerator()
                content = generator.generate_skill(safe_name, context)
            except ImportError as e:
                print(f"[!] Warning: AI provider not available ({e}). Falling back to standard parsing.")
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
                    
                    # (Extraction logic kept same)
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

    def generate_from_readme(
        self,
        readme_content: str,
        tech_stack: List[str],
        output_dir: Path,
        project_name: str = "",
        project_path: Optional[Path] = None,
    ) -> List[str]:
        """Generate project-specific learned skills from README and tech stack.

        Derives skill names from the actual technologies detected in the project
        instead of using generic category names.

        Args:
            readme_content: Raw README text
            tech_stack: Detected tech names
            output_dir: .clinerules dir (kept for compatibility, though self.project_local_dir preferred)
            project_name: Project name
            project_path: Project root
        """
        # Prefer the manager's project local dir if available, else derive from output_dir
        if self.project_local_dir:
            target_dir = self.project_local_dir
        else:
            target_dir = output_dir / 'skills' / 'project'
        
        target_dir.mkdir(parents=True, exist_ok=True)

        # Map tech to project-specific skill definitions
        skill_templates = self._derive_project_skills(tech_stack, readme_content, project_name)

        generated = []
        for skill_name, skill_content in skill_templates.items():
            dest = target_dir / f"{skill_name}.md"
            if dest.exists():
                # Overwrite if existing file is a generic stub or hallucinated
                if self._is_generic_stub(dest, project_path=project_path):
                    dest.write_text(skill_content, encoding='utf-8')
                    generated.append(skill_name)
            else:
                dest.write_text(skill_content, encoding='utf-8')
                generated.append(skill_name)

        return generated

    @staticmethod
    def _is_generic_stub(filepath: Path, project_path: Optional[Path] = None) -> bool:
        """Check if a skill file is a generic stub or contains hallucinations.

        Detects:
        1. Generic template markers (empty boilerplate)
        2. Hallucinated file paths (src/ references to non-existent dirs)
        3. Fabricated library imports not in project dependencies
        """
        try:
            content = filepath.read_text(encoding='utf-8', errors='replace')
        except Exception:
            return False

        # 1. Generic stub markers
        stub_markers = [
            'Follow project conventions',
            'Patterns and best practices for',
            '[One sentence: what problem does this solve]',
            '[When should agent activate this skill]',
            '[Step-by-step instructions]',
            'Working with general code',
            'Add tests for new functionality',
        ]
        if any(marker in content for marker in stub_markers):
            return True

        # 2. Hallucinated file path detection
        # Look for "File: src/..." or "src/something.py" references
        hallucinated_paths = re.findall(r'(?:File:\s*)?src/[\w/]+\.py(?::\d+)?', content)
        if hallucinated_paths and project_path:
            src_dir = project_path / 'src'
            if not src_dir.exists():
                # src/ directory doesn't exist — these are fabricated paths
                return True

        # 3. Detect fake file path patterns in code blocks (common hallucination)
        # e.g., "# File: src/main.py:25" in code examples
        file_refs = re.findall(r'#\s*File:\s*(\S+)', content)
        if file_refs and project_path:
            fake_count = 0
            for ref in file_refs:
                # Strip line number suffix
                ref_path = ref.split(':')[0]
                full_path = project_path / ref_path
                if not full_path.exists():
                    fake_count += 1
            # If majority of file refs are fake, it's hallucinated
            if fake_count > 0 and fake_count >= len(file_refs) / 2:
                return True

        return False

    # Tech name → preferred skill filename
    TECH_SKILL_NAMES = {
        'fastapi': 'fastapi-endpoints',
        'flask': 'flask-routes',
        'django': 'django-views',
        'express': 'express-routes',
        'react': 'react-components',
        'vue': 'vue-components',
        'pytest': 'pytest-testing',
        'jest': 'jest-testing',
        'docker': 'docker-deployment',
        'sqlalchemy': 'sqlalchemy-models',
        'celery': 'celery-tasks',
        'pydantic': 'pydantic-validation',
        'click': 'click-cli',
        'typer': 'typer-cli',
        'websocket': 'websocket-handler',
        'websockets': 'websocket-handler',
        'graphql': 'graphql-schema',
        'redis': 'redis-caching',
        'mongodb': 'mongodb-queries',
        'postgresql': 'postgresql-queries',
        'pytorch': 'pytorch-training',
        'tensorflow': 'tensorflow-models',
        'openai': 'openai-api',
        'anthropic': 'anthropic-api',
        'groq': 'groq-api',
        'gemini': 'gemini-api',
        'perplexity': 'perplexity-api',
        'langchain': 'langchain-chains',
        'httpx': 'httpx-client',
        'requests': 'requests-client',
        'chrome': 'chrome-extension',
        'chrome-extension': 'chrome-extension',
        'gitpython': 'gitpython-ops',
        'mcp': 'mcp-protocol',
        'uvicorn': 'uvicorn-server',
        'aiohttp': 'aiohttp-client',
    }

    def _derive_project_skills(
        self,
        tech_stack: List[str],
        readme_content: str,
        project_name: str,
    ) -> Dict[str, str]:
        """Derive project-specific skill names and content from tech stack.

        Extracts actual context from the README for each technology instead
        of using generic templates.
        """
        skills = {}
        seen_names = set()

        for tech in tech_stack:
            tech_lower = tech.lower().strip()
            skill_name = self.TECH_SKILL_NAMES.get(tech_lower)
            if not skill_name or skill_name in seen_names:
                continue
            seen_names.add(skill_name)

            # Extract README context for this specific tech
            context_lines = self._extract_tech_context(tech, readme_content)
            title = skill_name.replace('-', ' ').title()

            purpose = self._summarize_purpose(tech, context_lines, project_name)
            triggers = self._build_triggers(tech, context_lines)
            guidelines = self._build_guidelines(tech, context_lines)

            content = f"# {title}\n\n"
            content += f"**Project:** {project_name or 'this project'}\n\n"
            content += f"## Purpose\n\n{purpose}\n\n"
            content += f"## Auto-Trigger\n\n{triggers}\n\n"
            content += f"## Guidelines\n\n{guidelines}\n"

            if context_lines:
                content += f"\n## Project Context (from README)\n\n"
                for line in context_lines:
                    content += f"> {line}\n"

            skills[skill_name] = content

        return skills

    @staticmethod
    def _clean_markdown(text: str) -> str:
        """Strip markdown formatting from a line."""
        s = text.strip()
        # Remove leading list markers and arrows
        s = re.sub(r'^[-*→>]\s*', '', s)
        s = re.sub(r'^→+\s*', '', s)
        # Remove bold/italic markers
        s = s.replace('**', '').replace('*', '')
        # Remove link syntax [text](url) → text
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
        # Remove badge images ![alt](url)
        s = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', s)
        # Remove inline code backticks (keep content)
        s = s.replace('`', '')
        # Collapse multiple spaces
        s = re.sub(r'\s{2,}', ' ', s).strip()
        return s

    def _extract_tech_context(self, tech: str, readme_content: str) -> List[str]:
        """Extract lines from README that mention a specific technology."""
        lines = readme_content.split('\n')
        context = []
        tech_lower = tech.lower()

        # Also match common aliases
        aliases = {tech_lower}
        alias_map = {
            'fastapi': {'fastapi', 'fast api'},
            'websocket': {'websocket', 'websockets', 'web socket'},
            'perplexity': {'perplexity', 'sonar'},
            'openai': {'openai', 'gpt-4', 'gpt-3', 'chatgpt'},
            'pytorch': {'pytorch', 'torch'},
            'chrome': {'chrome', 'chrome extension', 'manifest.json', 'background.js', 'content script'},
            'gitpython': {'gitpython', 'git diff', 'git operations', 'repo.git'},
            'mcp': {'mcp', 'model context protocol', 'mcp server', 'mcp tool'},
        }
        if tech_lower in alias_map:
            aliases = alias_map[tech_lower]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(alias in line_lower for alias in aliases):
                stripped = line.strip()
                # Skip code fence lines, table separators, empty
                if not stripped or stripped.startswith('```') or stripped.startswith('|--'):
                    continue
                if stripped not in context:
                    context.append(stripped)
                    # Also grab the next line if it's a continuation
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if (next_line and not next_line.startswith('#')
                                and not next_line.startswith('```')
                                and next_line not in context):
                            context.append(next_line)

        return context[:10]

    def _summarize_purpose(self, tech: str, context_lines: List[str], project_name: str) -> str:
        """Build a purpose statement from extracted context."""
        if not context_lines:
            return f"Integration patterns for {tech} in {project_name or 'this project'}."

        # Find the most descriptive line — skip commands, tables, arrows-only
        best = ""
        for line in context_lines:
            clean = self._clean_markdown(line)
            # Skip non-descriptive lines
            if (clean.startswith('#') or clean.startswith('|')
                    or clean.startswith('pip ') or clean.startswith('npm ')
                    or clean.startswith('uvicorn ') or clean.startswith('docker ')
                    or len(clean) < 10):
                continue
            # Prefer lines that look like prose (has spaces, no excessive arrows)
            arrow_count = clean.count('→') + clean.count('->')
            if arrow_count > 2:
                continue
            if len(clean) > len(best):
                best = clean

        if best:
            return f"How {project_name or 'this project'} uses {tech}: {best}"
        return f"Integration patterns for {tech} in {project_name or 'this project'}."

    def _build_triggers(self, tech: str, context_lines: List[str]) -> str:
        """Build auto-trigger rules from context."""
        triggers = []

        # Extract file types and patterns mentioned in context
        for line in context_lines:
            # Look for file references
            files = re.findall(r'(\w+\.(?:py|js|ts|jsx|tsx|yaml|yml|json|toml))', line)
            for f in files:
                trigger = f"- Editing or creating `{f}`"
                if trigger not in triggers:
                    triggers.append(trigger)

            # Look for command/import patterns
            imports = re.findall(r'(?:import|from)\s+(\w+)', line)
            for imp in imports:
                if imp.lower() in tech.lower() or tech.lower() in imp.lower():
                    trigger = f"- Files importing `{imp}`"
                    if trigger not in triggers:
                        triggers.append(trigger)

        # Always add the base trigger
        triggers.append(f"- Working with {tech} integration code")
        triggers.append(f"- Editing files that import or configure {tech}")

        return '\n'.join(triggers)

    def _build_guidelines(self, tech: str, context_lines: List[str]) -> str:
        """Build guidelines from extracted project context."""
        guidelines = []

        for line in context_lines:
            clean = self._clean_markdown(line)
            # Skip non-actionable lines
            if (not clean or clean.startswith('#') or clean.startswith('|')
                    or len(clean) < 10):
                continue
            # Skip raw shell commands
            if re.match(r'^(pip |npm |yarn |uvicorn |docker |git clone|cd |mkdir )', clean):
                continue
            # Skip lines that are mostly arrows/diagrams
            if clean.count('→') + clean.count('->') > 2:
                continue

            # Lines describing architecture, config, or usage are useful
            if ':' in clean and len(clean) < 200:
                guidelines.append(f"- {clean}")
            elif re.search(r'(model|endpoint|config|api|key|token|port|host|stream|async|route|setup)', clean, re.I):
                guidelines.append(f"- {clean}")

        if not guidelines:
            guidelines.append(f"- Follow project patterns for {tech} usage")

        guidelines.append(f"- Handle {tech} errors with proper retries and fallbacks")
        guidelines.append(f"- Add tests for {tech} integration code")

        return '\n'.join(guidelines[:8])

    def get_all_skills_content(self) -> Dict[str, Dict]:
        """Get full content of all skills for export (Project > Learned > Builtin)."""
        self.ensure_global_structure()

        skills_content = {
            'project': {},
            'learned': {},
            'builtin': {}
        }
        
        # Helper to read skills
        def _read_skills_from_path(path: Path, category: str):
            if not path or not path.exists():
                return
            skills_list = self._scan_directory(path)
            for skill_rel_path in skills_list:
                # Skill list returns derived names
                # Try to find actual file
                
                # Check 1: MD in root
                md_path = path / f"{skill_rel_path}.md"
                # Check 2: SKILL.md in dir
                dir_md_path = path / skill_rel_path / "SKILL.md"
                # Check 3: YAML
                yaml_path = path / f"{skill_rel_path}.yaml"
                
                skill_file = None
                if md_path.exists(): skill_file = md_path
                elif dir_md_path.exists(): skill_file = dir_md_path
                elif yaml_path.exists(): skill_file = yaml_path
                
                if skill_file:
                    content = skill_file.read_text(encoding='utf-8', errors='replace')
                    # Use leaf name for simple ID
                    skill_name = skill_rel_path.split('/')[-1] 
                    skills_content[category][skill_name] = {
                        'path': str(skill_file),
                        'content': content
                    }

        _read_skills_from_path(self.global_builtin, 'builtin')
        _read_skills_from_path(self.global_learned, 'learned')
        if self.project_local_dir:
            _read_skills_from_path(self.project_local_dir, 'project')
        
        return skills_content

    def extract_all_triggers(self) -> Dict[str, List[str]]:
        """
        Extract auto-trigger phrases from all skills (Project > Learned > Builtin).
        Returns: { 'skill_name': ['phrase 1', 'phrase 2'] }
        """
        triggers = {}
        all_skills = self.get_all_skills_content()
        
        # We iterate in reverse priority (Builtin -> Learned -> Project) 
        # so higher priority overwrites lower if names collide (which they shouldn't usually, but good practice)
        # Actually, get_all_skills_content returns dict of dicts.
        
        for category in ['builtin', 'learned', 'project']:
            if category not in all_skills: continue
            
            for skill_name, skill_data in all_skills[category].items():
                content = skill_data['content']
                

                # Match "## Auto-Trigger" section
                match = re.search(r'## Auto-Trigger\n(.*?)(?:\n## |\Z)', content, re.DOTALL)
                if match:
                    trigger_text = match.group(1)
                    conditions = []
                    for line in trigger_text.split('\n'):
                        line = line.strip()
                        if not line.startswith('-'):
                            continue
                        
                        # Clean line
                        clean_line = line.strip('- ').strip().lower()
                        
                        # improved parsing: extract phrases in quotes
                        # e.g. - User says: "improve readme", "fix bug"
                        quoted_phrases = re.findall(r'"([^"]*)"', clean_line)
                        if quoted_phrases:
                            conditions.extend(quoted_phrases)
                        else:
                            # If no quotes, use the whole line but remove common prefixes
                            # e.g. "when requirements are unclear" -> "requirements are unclear"
                            for prefix in ['user says:', 'user reports:', 'when ', 'before ', 'after ']:
                                if clean_line.startswith(prefix):
                                    clean_line = clean_line[len(prefix):].strip()
                            conditions.append(clean_line)
                    
                    if conditions:
                        # If project overrides builtin, we want the project's triggers?
                        # Or maybe we just use the name as key.
                        # Since resolve_skill handles priority, we just map name -> triggers.
                        # If a skill is shadowed, its triggers are replaced by the shadowing skill's triggers.
                        triggers[skill_name] = conditions
        
        return triggers

    def save_triggers_json(self, output_dir: Path):
        """Save extracted triggers to .clinerules/auto-triggers.json"""
        import json
        
        triggers = self.extract_all_triggers()
        output_file = output_dir / "auto-triggers.json"
        
        try:
            output_file.write_text(json.dumps(triggers, indent=2), encoding='utf-8')
        except Exception as e:
            print(f"[Warning] Failed to save auto-triggers.json: {e}")

