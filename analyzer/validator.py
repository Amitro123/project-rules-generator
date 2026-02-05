"""Validate project data and generated content quality."""
import re
from typing import Dict, List, Any, Tuple


class ValidationResult:
    """Container for validation results."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0
    
    def add_error(self, msg: str):
        self.errors.append(msg)
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)
    
    def add_info(self, msg: str):
        self.info.append(msg)
    
    def merge(self, other: 'ValidationResult'):
        """Merge another result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)


def validate_project_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate extracted project data quality."""
    result = ValidationResult()
    
    # Required fields
    if not data.get('name') or data['name'] == 'unknown':
        result.add_error("Project name is missing or could not be detected")
    
    # Name format check
    if data.get('name'):
        if not re.match(r'^[a-z0-9-]+$', data['name']):
            result.add_warning(f"Project name '{data['name']}' contains special characters")
    
    # Description quality
    desc = data.get('description', '')
    if not desc:
        result.add_warning("No description extracted from README")
    elif len(desc) < 20:
        result.add_warning(f"Description is very short ({len(desc)} chars)")
    elif len(desc) > 500:
        result.add_info(f"Description truncated to 500 chars (was longer)")
    
    # Tech stack
    tech = data.get('tech_stack', [])
    if not tech:
        result.add_warning("No tech stack detected in README")
    else:
        result.add_info(f"Detected {len(tech)} technologies: {', '.join(tech)}")
    
    # Features
    features = data.get('features', [])
    if not features:
        result.add_warning("No features detected")
    elif len(features) < 3:
        result.add_info(f"Only {len(features)} features detected")
    else:
        result.add_info(f"Detected {len(features)} features")
    
    # README content check
    raw = data.get('raw_readme', '')
    if len(raw) < 100:
        result.add_warning("README content is very short")
    
    if '---' not in raw and not any(h in raw for h in ['## ', '### ']):
        result.add_warning("README may lack proper structure (no headers found)")
    
    return result


def validate_generated_content(content: str, content_type: str) -> ValidationResult:
    """Validate generated markdown content."""
    result = ValidationResult()
    
    # Check for frontmatter
    if not content.startswith('---'):
        result.add_error(f"Missing YAML frontmatter in {content_type}")
    
    # Check required sections for rules
    if content_type == 'rules':
        required_sections = ['CONTEXT', 'DO', "DON'T", 'PRIORITIES', 'WORKFLOWS']
        for section in required_sections:
            if f'## {section}' not in content and f'## {section.upper()}' not in content:
                result.add_error(f"Missing required section: {section}")
    
    # Check required sections for skills
    if content_type == 'skills':
        required_sections = ['CORE SKILLS', 'PROJECT-SPECIFIC', 'USAGE']
        for section in required_sections:
            if section.upper() not in content.upper():
                result.add_warning(f"Missing recommended section: {section}")
    
    # Check markdown quality
    if '***' not in content:
        result.add_warning("Missing document separator (***)")
    
    # Check for placeholders that weren't replaced
    placeholders = re.findall(r'\{([^}]+)\}', content)
    if placeholders:
        result.add_warning(f"Unreplaced placeholders found: {placeholders}")
    
    # Length check
    lines = content.split('\n')
    if len(lines) < 10:
        result.add_warning(f"Content seems short ({len(lines)} lines)")
    
    return result


def check_markdown_syntax(content: str) -> List[str]:
    """Check for common markdown syntax issues."""
    issues = []
    
    # Check for unclosed code blocks
    code_blocks = re.findall(r'```', content)
    if len(code_blocks) % 2 != 0:
        issues.append("Unclosed code block detected")
    
    # Check for broken links [text]()
    broken_links = re.findall(r'\[([^\]]+)\]\(\s*\)', content)
    if broken_links:
        issues.append(f"Empty links: {broken_links}")
    
    # Check for heading level skips
    headings = re.findall(r'^(#{1,6})\s', content, re.MULTILINE)
    if headings:
        levels = [len(h) for h in headings]
        for i, level in enumerate(levels[1:], 1):
            if level > levels[i-1] + 1:
                issues.append(f"Heading level jump: {levels[i-1]} to {level}")
    
    return issues
