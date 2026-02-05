from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Skill:
    name: str
    description: str
    category: str = "general" # core, tech, ml_pipeline, agent, etc.
    triggers: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    when_to_use: List[str] = field(default_factory=list)
    avoid_if: List[str] = field(default_factory=list)
    input_desc: Optional[str] = None
    output_desc: Optional[str] = None
    usage_example: Optional[str] = None
    source: str = "project"  # project, agent-rules, vercel-agent-skills, etc.
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "triggers": self.triggers,
            "tools": self.tools,
            "when_to_use": self.when_to_use,
            "avoid_if": self.avoid_if,
            "input": self.input_desc,
            "output": self.output_desc,
            "usage": self.usage_example,
            "params": getattr(self, "params", {}), # Safe access for debugging
            "source": getattr(self, "source", "unknown")
        }

@dataclass
class SkillPack:
    name: str
    description: str = ""
    skills: List[Skill] = field(default_factory=list)

@dataclass
class SkillFile:
    project_name: str
    project_type: str
    skills: List[Skill]
    confidence: float
    tech_stack: List[str]
    description: str = ""
    version: str = "1.0"
