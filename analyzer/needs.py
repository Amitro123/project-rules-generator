from typing import List, Dict, Any
from generator.types import SkillNeed
from analyzer.project_type_detector import detect_project_type_from_data

class ProjectNeedsAnalyzer:
    """Analyzes project data to identify skill needs."""
    
    def analyze(self, project_data: Dict[str, Any], project_path: str) -> List[SkillNeed]:
        """
        Convert project metadata into a list of specific needs.
        
        Args:
            project_data: Data from readme_parser (tech_stack, features, etc.)
            project_path: Root path of the project
            
        Returns:
            List[SkillNeed] with priorities
        """
        needs = []
        
        # 1. Project Type Need (Critical)
        # Re-run detection or use existing if passed? 
        # For better decoupling, we might want to assume detection happened externaly or do it here.
        # Let's trust detection was done or do it quickly.
        type_info = detect_project_type_from_data(project_data, str(project_path))
        primary_type = type_info['primary_type']
        confidence = type_info['confidence']
        
        needs.append(SkillNeed(
            type="project_type",
            name=primary_type,
            confidence=confidence,
            priority="critical",
            context={"secondary_types": type_info['secondary_types']}
        ))
        
        # 2. Tech Stack Needs (Normal)
        tech_stack = project_data.get('tech_stack', [])
        for tech in tech_stack:
            needs.append(SkillNeed(
                type="tech",
                name=tech,
                confidence=1.0, # Explicitly stated in README
                priority="normal",
                context={}
            ))
            # Also imply expert need
            needs.append(SkillNeed(
                type="tech",
                name=f"{tech}-expert",
                confidence=0.9,
                priority="optional",
                context={}
            ))

        # 3. Core Need (Always present)
        needs.append(SkillNeed(
            type="core",
            name="core",
            confidence=1.0,
            priority="critical"
        ))
        
        return needs
