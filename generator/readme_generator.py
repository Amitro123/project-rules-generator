"""Interactive README generation."""

from pathlib import Path
import click
from typing import Dict, Optional

def is_readme_minimal(readme_path: Path) -> bool:
    """Check if README is too minimal to be useful."""
    if not readme_path.exists():
        return True
    
    try:
        content = readme_path.read_text(encoding='utf-8')
        
        # Criteria for "minimal"
        if len(content) < 200:  # Less than 200 chars
            return True
        if content.count('\n') < 5:  # Less than 5 lines
            return True
        
        # Check for placeholders and template artifacts
        placeholders = [
            'TODO', 
            'PLACEHOLDER',
            '(one per line',
            'Add features here',
            'Add your run command here',
            'Various technologies',
            'A brief description of the project'
        ]
        
        content_upper = content.upper()
        for p in placeholders:
            if p.upper() in content_upper:
                return True
        
        return False
    except Exception:
        return True



from generator.utils import flush_input

def generate_readme_interactively(project_path: Path, use_ai: bool) -> str:
    """Generate README through user prompts and LLM."""
    
    click.echo("\n" + "="*60)
    click.echo("📚 Interactive README Generation")
    click.echo("="*60 + "\n")
    click.echo("Let's create a README for your project!\n")
    
    # Gather user input
    user_input = {}
    
    flush_input()
    user_input['name'] = click.prompt(
        "Project name",
        default=project_path.name
    )
    
    user_input['description'] = click.prompt(
        "One-line description",
        default=""
    )
    
    user_input['purpose'] = click.prompt(
        "What problem does it solve?",
        default=""
    )
    
    user_input['tech_stack'] = click.prompt(
        "Main technologies (comma-separated)",
        default=""
    )
    
    user_input['features'] = click.prompt(
        "Key features (comma-separated)",
        default=""
    )
    
    # Scan project structure
    click.echo("\n🔍 Scanning project structure...")
    from generator.project_analyzer import ProjectAnalyzer
    analyzer = ProjectAnalyzer(project_path)
    context = analyzer.analyze()
    
    if use_ai:
        # Use LLM to generate README
        click.echo("🤖 Generating README with AI...\n")
        readme_content = generate_readme_with_llm(user_input, context)
    else:
        # Use template
        readme_content = generate_readme_template(user_input, context)
    
    # Preview
    click.echo("="*60)
    click.echo("📄 Generated README Preview:")
    click.echo("="*60)
    preview = readme_content[:600] + ("\n...\n(truncated)" if len(readme_content) > 600 else "")
    click.echo(preview)
    click.echo("="*60 + "\n")
    
    flush_input()
    if not click.confirm("Save this README?", default=True):
        click.echo("❌ Cancelled.")
        raise click.Abort()
    
    return readme_content


def generate_readme_with_llm(user_input: Dict, context: Dict, provider: str = 'gemini', api_key: Optional[str] = None) -> str:
    """Generate README using AI."""
    try:
        from generator.llm_skill_generator import LLMSkillGenerator

        # Format tech stack
        tech_detected = []
        for category in ['backend', 'frontend', 'database', 'languages']:
            if context['tech_stack'].get(category):
                tech_detected.extend(context['tech_stack'][category])
        
        tech_str = ', '.join(tech_detected) if tech_detected else "Unknown"
        
        prompt = f"""# Generate Professional README.md

## User Input
- **Project Name**: {user_input['name']}
- **Description**: {user_input['description']}
- **Purpose**: {user_input['purpose']}
- **Tech Stack (User)**: {user_input['tech_stack']}
- **Key Features**: {user_input['features']}

## Auto-Detected Context
- **Tech Stack (Detected)**: {tech_str}
- **Has Backend**: {context['structure'].get('has_backend', False)}
- **Has Frontend**: {context['structure'].get('has_frontend', False)}
- **Has Tests**: {context['structure'].get('has_tests', False)}
- **Has Docker**: {context['structure'].get('has_docker', False)}

## Task

Generate a **professional, complete README.md** with these sections:

### Required Sections:
1. **Title & Badge** (if applicable)
2. **Description** (expand on user's input)
3. **Key Features** (bullet list, expand on user's input)
4. **Tech Stack** (combine detected + user input)
5. **Quick Start**
   - Prerequisites
   - Installation steps (infer from structure)
   - Running the project
6. **Project Structure** (brief, based on detected dirs)
7. **Usage** (if applicable)
8. **License** (MIT)

### Guidelines:
- Use actual commands based on detected tech
- Be specific, not generic
- Include code blocks for commands
- Professional but concise
- No placeholders or TODOs

Generate the complete README now:
"""
        
        generator = LLMSkillGenerator()
        return generator.generate_content(prompt, max_tokens=3000)
    except Exception as e:
        click.echo(f"⚠️  LLM generation failed: {e}", err=True)
        click.echo("Falling back to template...")
        return generate_readme_template(user_input, context)


def generate_readme_template(user_input: Dict, context: Dict) -> str:
    """Generate README from template (fallback)."""
    
    # Collect tech
    tech_list = []
    for category in ['backend', 'frontend', 'database']:
        if context['tech_stack'].get(category):
            tech_list.extend(context['tech_stack'][category])
    
    tech_display = ', '.join(tech_list) if tech_list else user_input.get('tech_stack', 'Various technologies')
    
    # Format features - Sanitize input
    raw_features = user_input.get('features', '')
    # Check for placeholder text capture
    if "comma-separated" in raw_features.lower() or "one per line" in raw_features.lower():
        raw_features = ""
        
    features = [f.strip() for f in raw_features.split(',') if f.strip()]
    features_md = '\n'.join([f"- **{feat}**" for feat in features]) if features else "- (Add features here)"
    
    # Installation steps
    install_steps = []
    if 'Python' in context['tech_stack'].get('languages', []):
        install_steps.append("pip install -r requirements.txt")
    if 'JavaScript/TypeScript' in context['tech_stack'].get('languages', []):
        install_steps.append("npm install")
    
    install_md = '\n'.join(install_steps) if install_steps else "# Install dependencies"
    
    readme = f"""# {user_input.get('name', 'My Project')}

{user_input.get('description', 'A brief description of the project.')}

## Purpose

{user_input.get('purpose', 'This project aims to solve...')}

## Key Features

{features_md}

## Tech Stack

{tech_display}

## Quick Start

### Prerequisites

- Python 3.8+ / Node.js 16+ (depending on your stack)
- Git

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd {user_input.get('name', 'project').lower().replace(' ', '-')}

# Install dependencies
{install_md}
```

### Running

```bash
# Run the application
# (Add your run command here)
```

## Project Structure

```text
{user_input.get('name', 'project')}/
├── {', '.join(context['structure'].get('main_directories', [])[:5])}
```

## License

MIT License
"""
    return readme
