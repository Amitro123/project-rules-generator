"""README parsing and metadata extraction"""
from pathlib import Path
from typing import Dict, List, Any, Union, Optional
import re

def parse_readme(readme_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Extract structured metadata from README.md.

    Args:
        readme_path: Path to README.md file

    Returns:
        Dict with keys: name, tech_stack, features, description, raw_readme

    Raises:
        FileNotFoundError: If README.md doesn't exist
        ValueError: If README is empty or malformed
    """
    path = Path(readme_path)

    if not path.exists():
        raise FileNotFoundError(f"README not found: {readme_path}")

    content = path.read_text(encoding='utf-8')

    if not content.strip():
        raise ValueError(f"README is empty: {readme_path}")

    # Pass project_path for dependency cross-referencing
    project_path = path.parent

    return {
        'name': _extract_project_name(content, path),
        'tech_stack': extract_tech_stack(content, project_path=project_path),
        'features': _extract_features(content),
        'description': _extract_description(content),
        'installation': _extract_section(content, ['installation', 'setup', 'getting started']),
        'usage': _extract_section(content, ['usage', 'how to run', 'quick start']),
        'troubleshooting': _extract_section(content, ['troubleshooting', 'faq', 'common issues', 'gotchas']),
        'raw_readme': content,
        'readme_path': str(path)
    }


def _extract_section(content: str, keywords: List[str]) -> str:
    """Extract content of a section matching keywords."""
    keyword_pattern = '|'.join(keywords)
    # Match ## Header (allowing for emojis/decoration)
    # e.g. "## 🚀 Installation" or "## Installation 📦"
    header_pattern = re.compile(
        rf'(?m)^(#+)\s*(?:[^a-zA-Z0-9\n]*)\s*(?:{keyword_pattern})\s*(?:[^a-zA-Z0-9\n]*)$', 
        re.IGNORECASE
    )
    
    match = header_pattern.search(content)
    if not match:
        return ""
        
    start_pos = match.end()
    level = len(match.group(1))
    
    # Find next header of same or higher level (fewer #s)
    # e.g. if we found ## Install, stop at ## Usage or # Title, but consume ### Sub-step
    next_header_pattern = re.compile(
        rf'(?m)^#{{1,{level}}}\s+'
    )
    
    next_match = next_header_pattern.search(content, start_pos)
    end_pos = next_match.start() if next_match else len(content)
    
    return content[start_pos:end_pos].strip()


def _extract_project_name(content: str, path: Path) -> str:
    """Extract project name from first H1 heading."""
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        name = match.group(1).strip()
        # Clean badges, emojis, extra text
        name = re.sub(r'\[!\[.*?\]\(.*?\)\]', '', name)  # Remove badges
        name = re.sub(r'[🎯🚀✨🔥💡]', '', name)  # Remove emojis
        name = re.sub(r'[^\w\s-]', '', name).lower().strip()
        name = re.sub(r'\s+', '-', name)
        return name
    
    # Fallback: use directory name
    return path.parent.name.lower().replace(' ', '-')


TECH_KEYWORDS = [
    'python', 'fastapi', 'flask', 'django', 'react', 'vue', 'angular',
    'typescript', 'javascript', 'node', 'express',
    'pytorch', 'tensorflow', 'sklearn', 'transformers',
    'docker', 'kubernetes', 'redis', 'postgres', 'mongodb',
    'gemini', 'openai', 'anthropic', 'claude', 'gpt', 'langchain',
    'perplexity', 'groq', 'mistral', 'cohere',
    'ffmpeg', 'opencv', 'pillow', 'moviepy', 'whisper',
    'click', 'argparse', 'typer', 'fire',
    'terraform', 'helm', 'aws', 'gcp', 'azure',
    # Web/realtime
    'websocket', 'graphql', 'grpc',
    # HTTP clients
    'httpx', 'aiohttp',
    # Python ecosystem
    'pydantic', 'uvicorn', 'celery', 'sqlalchemy',
    # Git/VCS
    'gitpython',
    # Chrome/browser
    'chrome',
    # Protocols/tools
    'mcp',
]


def extract_tech_stack(content: str, project_path: Optional[Path] = None) -> List[str]:
    """Extract technologies from README content, validated against actual dependencies.

    Args:
        content: README text content
        project_path: Optional path to project root for dependency cross-referencing
    """

    # Remove sections that typically contain examples, comparisons, docs, or illustrative content
    ignore_section_keywords = (
        r'Example|Sample|Supported|Comparison|vs\b|FAQ|'
        r'How It Works|What Makes|Wow Moment|Scenario|'
        r'Real.World|Impact|Contributing|License'
    )
    ignore_pattern = rf'(?m)^\s*#+\s*.*(?:{ignore_section_keywords}).*$(?:\n(?!^\s*#+).*)*'
    content_cleaned = re.sub(ignore_pattern, '', content, flags=re.IGNORECASE)

    # Strip code blocks (```...```)
    content_cleaned = re.sub(r'```[\s\S]*?```', '', content_cleaned)

    # Strip mermaid/diagram blocks
    content_cleaned = re.sub(r'```mermaid[\s\S]*?```', '', content_cleaned)

    # Strip inline code (`...`) to avoid matching tech names in code refs
    content_cleaned = re.sub(r'`[^`]+`', '', content_cleaned)

    # Strip markdown tables (lines starting with |)
    content_cleaned = re.sub(r'(?m)^\|.*\|$', '', content_cleaned)

    # Strip markdown image/badge syntax
    content_cleaned = re.sub(r'!\[.*?\]\(.*?\)', '', content_cleaned)
    content_cleaned = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', content_cleaned)

    content_lower = content_cleaned.lower()
    found = [tech for tech in TECH_KEYWORDS if re.search(rf'\b{re.escape(tech)}\b', content_lower)]

    # Cross-reference with actual dependencies if project_path is provided
    if project_path:
        found = _validate_tech_with_deps(found, Path(project_path))

    # Remove duplicates, preserve order
    return list(dict.fromkeys(found))


def _validate_tech_with_deps(readme_tech: List[str], project_path: Path) -> List[str]:
    """Cross-reference README-detected tech with actual project dependencies.

    Keeps tech that is:
    - Found in requirements.txt / pyproject.toml / package.json / setup.py
    - Found as actual imports in source files
    - A language marker ('python', 'javascript', 'typescript') confirmed by file existence
    - Infrastructure confirmed by file existence (docker, kubernetes)

    If no dependency files exist at all, returns readme_tech unchanged (nothing to validate against).
    """
    # If no dependency files exist, skip validation entirely
    dep_files = ['requirements.txt', 'requirements-dev.txt', 'requirements-llm.txt',
                 'pyproject.toml', 'package.json', 'setup.py', 'setup.cfg']
    has_any_deps = any((project_path / f).exists() for f in dep_files)
    has_any_source = list(project_path.glob('*.py')) or (project_path / 'package.json').exists()
    if not has_any_deps and not has_any_source:
        return readme_tech

    # Always-valid: confirmed by checking actual files, not README
    confirmed = set()

    # Language detection from files
    if (project_path / 'requirements.txt').exists() or list(project_path.glob('*.py')):
        confirmed.add('python')
    if (project_path / 'package.json').exists():
        confirmed.add('javascript')
        confirmed.add('node')

    # Infrastructure from files
    if (project_path / 'Dockerfile').exists():
        confirmed.add('docker')
    if (project_path / 'docker-compose.yml').exists() or (project_path / 'docker-compose.yaml').exists():
        confirmed.add('docker')
    if any(project_path.glob('*.tf')):
        confirmed.add('terraform')

    # Read actual dependency files
    dep_content = ''
    for dep_file in ['requirements.txt', 'requirements-dev.txt', 'requirements-llm.txt']:
        dep_path = project_path / dep_file
        if dep_path.exists():
            try:
                dep_content += dep_path.read_text(encoding='utf-8', errors='replace').lower() + '\n'
            except Exception:
                pass

    # pyproject.toml
    pyproject = project_path / 'pyproject.toml'
    if pyproject.exists():
        try:
            dep_content += pyproject.read_text(encoding='utf-8', errors='replace').lower() + '\n'
        except Exception:
            pass

    # package.json
    pkg_json = project_path / 'package.json'
    if pkg_json.exists():
        try:
            dep_content += pkg_json.read_text(encoding='utf-8', errors='replace').lower() + '\n'
        except Exception:
            pass

    # Map tech keywords to dependency patterns
    tech_to_dep_patterns = {
        'fastapi': ['fastapi'],
        'flask': ['flask'],
        'django': ['django'],
        'react': ['react', '"react"', "'react'"],
        'vue': ['vue', '"vue"', "'vue'"],
        'angular': ['@angular'],
        'express': ['express'],
        'pytorch': ['torch', 'pytorch'],
        'tensorflow': ['tensorflow'],
        'sklearn': ['scikit-learn', 'sklearn'],
        'transformers': ['transformers'],
        'redis': ['redis'],
        'postgres': ['psycopg', 'postgresql', 'postgres'],
        'mongodb': ['pymongo', 'mongodb', 'mongoose'],
        'gemini': ['google-generativeai', 'google-genai', 'gemini'],
        'openai': ['openai'],
        'anthropic': ['anthropic'],
        'claude': ['anthropic'],
        'langchain': ['langchain'],
        'perplexity': ['perplexity', 'perplexity-ai', 'pplx'],
        'groq': ['groq'],
        'mistral': ['mistral', 'mistralai'],
        'cohere': ['cohere'],
        'ffmpeg': ['ffmpeg'],
        'opencv': ['opencv', 'cv2'],
        'pillow': ['pillow', 'pil'],
        'moviepy': ['moviepy'],
        'whisper': ['whisper', 'openai-whisper'],
        'click': ['click'],
        'argparse': ['argparse'],
        'typer': ['typer'],
        'fire': ['python-fire', 'fire'],
        'kubernetes': ['kubernetes'],
        'typescript': ['typescript'],
        'gpt': ['openai'],
        'helm': ['helm'],
        'aws': ['boto3', 'aws-cdk', 'aws'],
        'gcp': ['google-cloud', 'gcp'],
        'azure': ['azure'],
        'websocket': ['websockets', 'websocket', 'socket.io'],
        'graphql': ['graphql', 'ariadne', 'strawberry'],
        'grpc': ['grpcio', 'grpc'],
        'httpx': ['httpx'],
        'aiohttp': ['aiohttp'],
        'pydantic': ['pydantic'],
        'uvicorn': ['uvicorn'],
        'celery': ['celery'],
        'sqlalchemy': ['sqlalchemy'],
        'gitpython': ['gitpython'],
        'chrome': ['chrome', 'manifest'],
        'mcp': ['mcp'],
    }

    # Check each README-detected tech against deps
    validated = []
    for tech in readme_tech:
        # Already confirmed by file existence
        if tech in confirmed:
            validated.append(tech)
            continue

        # Check against dependency content
        patterns = tech_to_dep_patterns.get(tech, [tech])
        if any(pat in dep_content for pat in patterns):
            confirmed.add(tech)
            validated.append(tech)

    # Also ADD tech from actual dependencies not found in README
    # (e.g., "click" only appears in code blocks which get stripped)
    dep_to_tech_reverse = {}
    for tech_name, patterns in tech_to_dep_patterns.items():
        for pat in patterns:
            dep_to_tech_reverse[pat] = tech_name

    for pat, tech_name in dep_to_tech_reverse.items():
        if tech_name not in confirmed and pat in dep_content:
            validated.append(tech_name)
            confirmed.add(tech_name)

    return validated


def extract_purpose(readme: str) -> str:
    """Extract project purpose/description from README."""
    # Look for first paragraph after title
    lines = readme.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('# ') and i + 1 < len(lines):
            # Get first non-empty line after title
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and not lines[j].startswith('#'):
                    return lines[j].strip().rstrip('.')
    return "Solve project-specific workflow challenges"


def extract_auto_triggers(readme: str, skill_name: str) -> List[str]:
    """Generate auto-trigger suggestions."""
    triggers = []
    
    # From skill name
    name_words = skill_name.replace('-', ' ').split()
    quoted_words = [f'"{w}"' for w in name_words]
    triggers.append(f"User mentions: {', '.join(quoted_words)}")
    
    # From tech stack
    tech = extract_tech_stack(readme)
    if 'ffmpeg' in tech:
        triggers.append("FFmpeg operations needed")
    if any(t in tech for t in ['react', 'typescript', 'node']):
        triggers.append("Working in frontend code: *.tsx, *.jsx, *.ts")
    if 'python' in tech:
        triggers.append("Working in backend code: *.py")
    
    # File patterns from README
    if re.search(r'\*\.(mp4|avi|mov)', readme):
        triggers.append("Working with video files: *.mp4, *.avi, *.mov")
    
    return triggers


def extract_process_steps(readme: str) -> List[str]:
    """Extract installation/quickstart steps from README."""
    steps = []
    in_quickstart = False
    
    lines = readme.split('\n')
    for i, line in enumerate(lines):
        # Find Quick Start section
        if re.search(r'## .*(quick start|installation|setup)', line, re.IGNORECASE):
            in_quickstart = True
            continue
        
        if in_quickstart:
            # Stop at next ## section
            if line.startswith('## ') and not line.startswith('### '):
                break
            
            # Collect numbered steps or commands
            if re.match(r'^\d+\.', line.strip()):
                steps.append(line.strip())
            elif line.strip().startswith('```'):
                # Include code blocks
                code_block = []
                for j in range(i, len(lines)):
                    code_block.append(lines[j])
                    if j > i and lines[j].strip().startswith('```'):
                        break
                steps.append('\n'.join(code_block))
    
    return steps[:10]  # Limit to 10 steps


def extract_anti_patterns(readme: str, tech: List[str], project_path: Optional[Path] = None) -> List[str]:
    """Generate anti-patterns grounded in actual project analysis.

    Only returns patterns that can be verified against the actual project,
    not hypothetical issues.
    """
    anti_patterns = []

    if not project_path:
        return anti_patterns

    project_path = Path(project_path)

    # Check for missing system dependency guards
    if 'ffmpeg' in tech:
        # Verify ffmpeg is actually called in code
        for py_file in project_path.rglob('*.py'):
            if any(skip in py_file.parts for skip in ('.venv', 'venv', '__pycache__', '.git', 'node_modules')):
                continue
            try:
                content = py_file.read_text(encoding='utf-8', errors='replace')
                if 'ffmpeg' in content and 'shutil.which' not in content:
                    anti_patterns.append(
                        f"Missing FFmpeg availability check in {py_file.name} → "
                        "Add: `if not shutil.which('ffmpeg'): raise RuntimeError('ffmpeg not found')`"
                    )
                    break
            except Exception:
                pass

    # Check for missing type checking config
    if 'python' in tech or 'pydantic' in tech:
        has_mypy_config = (
            (project_path / 'mypy.ini').exists() or
            (project_path / '.mypy.ini').exists() or
            (project_path / 'setup.cfg').exists() or
            (project_path / 'pyproject.toml').exists()
        )
        if not has_mypy_config:
            anti_patterns.append(
                "No type checking config found → Run: `mypy --install-types --strict .`"
            )

    # Check for missing test configuration
    if 'pytest' in tech:
        has_pytest_config = any([
            (project_path / 'pytest.ini').exists(),
            (project_path / 'setup.cfg').exists(),
            (project_path / 'pyproject.toml').exists(),
        ])
        if not has_pytest_config:
            anti_patterns.append(
                "No pytest config found → Run: `pytest --co -q` to verify test discovery"
            )

    return anti_patterns


def _extract_features(content: str, max_features: int = 10) -> List[str]:
    """Extract feature list from README."""
    features = []
    
    # Look for features section
    features_section = re.search(
        r'(?:##?\s*(?:features|key|what|capabilities)|^)(.+?)(?=##?|$)',
        content, 
        re.DOTALL | re.MULTILINE | re.IGNORECASE
    )
    
    if features_section:
        section_text = features_section.group(1)
        # Find list items
        feature_matches = re.findall(r'(?:^|\n)[\s]*[\-\*✅]\s*(.+?)(?=\n[\-\*✅]|\n\n|$)', section_text)
        features = [f.strip() for f in feature_matches if len(f.strip()) > 5]
    
    # If no features found, look for any list items in first half of doc
    if not features:
        early_content = content[:len(content)//2]
        feature_matches = re.findall(r'(?:^|\n)[\s]*[\-\*✅]\s*(.+?)(?=\n[\-\*✅]|\n\n|$)', early_content)
        features = [f.strip() for f in feature_matches if 5 < len(f.strip()) < 200]
    
    return features[:max_features]


def _extract_description(content: str, max_length: int = 200) -> str:
    """Extract project description from README."""
    # Get first paragraph after title
    match = re.search(r'^#.+?\n\n(.+?)(?=\n\n##|\n\n#|$)', content, re.DOTALL | re.MULTILINE)
    if match:
        desc = match.group(1).strip()
        # Clean markdown formatting
        desc = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', desc)  # Remove links
        desc = re.sub(r'\*\*|\*|__|_', '', desc)  # Remove bold/italic
        desc = desc.replace('\n', ' ')
        return desc[:max_length].strip()
    
    # Fallback to first paragraph
    first_para = re.search(r'\n\n([\s\S]{20,500}?)(?=\n\n)', content)
    if first_para:
        desc = first_para.group(1).strip().replace('\n', ' ')
        return desc[:max_length].strip()
    
    return "No description available"
