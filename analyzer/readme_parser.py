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
        'tech_stack': _extract_tech_stack(content),
        'features': _extract_features(content),
        'description': _extract_description(content),
        'raw_readme': content,
        'readme_path': str(path)
    }


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


def _extract_tech_stack(content: str) -> List[str]:
    """Extract technologies from README content."""
    tech_keywords = [
        'python', 'fastapi', 'flask', 'django', 'react', 'vue', 'angular',
        'typescript', 'javascript', 'node', 'express',
        'pytorch', 'tensorflow', 'sklearn', 'transformers',
        'docker', 'kubernetes', 'redis', 'postgres', 'mongodb',
        'gemini', 'openai', 'anthropic', 'claude', 'gpt', 'langchain',
        'ffmpeg', 'opencv', 'pillow', 'moviepy',
        'click', 'argparse', 'typer', 'fire',
        'terraform', 'helm', 'aws', 'gcp', 'azure'
    ]
    
    content_lower = content.lower()
    found = [tech for tech in tech_keywords if re.search(rf'\b{re.escape(tech)}\b', content_lower)]
    
    # Remove duplicates, preserve order
    return list(dict.fromkeys(found))


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
