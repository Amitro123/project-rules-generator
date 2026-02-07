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
    
    return {
        'name': _extract_project_name(content, path),
        'tech_stack': extract_tech_stack(content),
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
    'ffmpeg', 'opencv', 'pillow', 'moviepy', 'whisper',
    'click', 'argparse', 'typer', 'fire',
    'terraform', 'helm', 'aws', 'gcp', 'azure'
]


def extract_tech_stack(content: str) -> List[str]:
    """Extract technologies from README content."""
    
    # Remove sections that typically contain examples or comparisons to avoid false positives
    # Matches headers containing keywords and all content until the next header
    ignore_pattern = r'(?m)^\s*#+\s*.*(?:Example|Sample|Supported|Comparison).*$(?:\n(?!^\s*#+).*)*'
    content_cleaned = re.sub(ignore_pattern, '', content)
    
    # Also strip code blocks to avoid matching tools in examples/config
    # This also helps avoid matching 'ffmpeg' in the JSON example
    content_cleaned = re.sub(r'```[\s\S]*?```', '', content_cleaned)

    content_lower = content_cleaned.lower()
    found = [tech for tech in TECH_KEYWORDS if re.search(rf'\b{re.escape(tech)}\b', content_lower)]
    
    # Remove duplicates, preserve order
    return list(dict.fromkeys(found))


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


def extract_anti_patterns(readme: str, tech: List[str]) -> List[str]:
    """Generate anti-patterns based on tech stack."""
    anti_patterns = []
    
    if 'ffmpeg' in tech:
        anti_patterns.append("Running without FFmpeg installed → Check first: `ffmpeg -version`")
    if 'redis' in tech:
        anti_patterns.append("Processing without Redis for queue management")
    if any(t in tech for t in ['whisper', 'gemini']):
        anti_patterns.append("Ignoring API rate limits")
    if 'docker' in tech:
        anti_patterns.append("Not using Docker for consistent environment")
    
    # Generic
    anti_patterns.append("Not testing before deployment")
    anti_patterns.append("Skipping error handling")
    
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
