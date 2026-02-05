"""Generate project-specific skills based on structured data"""
from typing import Dict, Any, Union, List
from pathlib import Path
from analyzer.project_type_detector import detect_project_type_from_data
from .types import Skill, SkillFile, SkillPack
from .skill_templates import load_skill_template, get_tech_skills, get_core_skills
from .renderers import get_renderer

def generate_skills(project_data: Dict[str, Any], config: Dict[str, Any], project_path: Union[str, Path] = '.', format: str = 'markdown', external_packs: List[SkillPack] = None) -> str:
    """Generate intelligent, project-specific skills
    
    Args:
        project_data: Parsed project data
        config: Configuration dict
        project_path: Path to project root
        format: Output format ('markdown', 'json', 'yaml')
        external_packs: Optional list of external skill packs to merge
        
    Returns:
        Rendered skills content
    """
    
    # Detect project type
    type_info = detect_project_type_from_data(project_data, str(project_path))
    primary_type = type_info['primary_type']
    secondary_types = type_info['secondary_types']
    
    project_name = project_data['name']
    tech = project_data.get('tech_stack', [])
    description = project_data.get('description', '')
    
    all_skills = []
    
    # 1. Add Core Skills
    core_skills = get_core_skills()
    all_skills.extend(core_skills)
    
    # 2. Add Tech Specific Skills
    tech_skills = get_tech_skills(tech)
    all_skills.extend(tech_skills)
    
    # 3. Add Primary Type Skills
    type_skills = load_skill_template(primary_type)
    for s in type_skills:
        s.category = primary_type # Ensure correct category
    all_skills.extend(type_skills)
    
    # 4. Add Secondary Type Skills (Top 1)
    for sec_type in secondary_types[:1]:
        if sec_type == 'generator':
            continue
        sec_skills = load_skill_template(sec_type)
        if sec_skills:
            # Add top 2 skills only to avoid bloat
            for s in sec_skills[:2]:
                s.category = sec_type
                all_skills.extend([s])

    # 5. Merge External Packs
    if external_packs:
        existing_names = {s.name for s in all_skills}
        for pack in external_packs:
            for skill in pack.skills:
                # Deduplicate: Only add if name doesn't exist (prefer project skills)
                if skill.name not in existing_names:
                    all_skills.append(skill)
                    existing_names.add(skill.name)

    # Fallback if no specific skills found for tech
    if not tech_skills and not type_skills and tech:
        primary_tech = tech[0]
        # Dynamically create a generic expert skill if we have no templates
        all_skills.append(Skill(
            name=f"{primary_tech}-expert",
            description=f"Expert in {primary_tech} projects, patterns, and best practices.",
            category="tech",
            when_to_use=[
                f"Complex {primary_tech} specific implementation",
                f"Debugging {primary_tech} errors"
            ]
        ))

    # Create SkillFile object
    skill_file = SkillFile(
        project_name=project_name,
        project_type=primary_type,
        skills=all_skills,
        confidence=type_info['confidence'],
        tech_stack=tech,
        description=description
    )
    
    # Render
    return get_renderer(format).render(skill_file)
