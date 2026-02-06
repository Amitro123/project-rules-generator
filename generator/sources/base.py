from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..types import Skill, SkillNeed

class SkillSource(ABC):
    """Abstract base class for a source of skills."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def discover(self, needs: List[SkillNeed]) -> List[Skill]:
        """
        Discover skills that match the provided needs.
        
        Args:
            needs: List of project skill needs.
            
        Returns:
            List of matching Skill objects.
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the skill source."""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Priority of the source (higher wins conflicts)."""
        pass
