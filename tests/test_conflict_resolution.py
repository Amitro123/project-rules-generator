import pytest
from unittest.mock import MagicMock
from generator.orchestrator import SkillOrchestrator
from generator.sources.base import SkillSource
from generator.types import Skill, SkillNeed

class MockSource(SkillSource):
    def __init__(self, name, priority_val, skills):
        self._name = name
        self._priority = priority_val
        self._skills = skills
        self.config = {} # Dummy

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    def discover(self, needs):
        # simple match by name for testing
        found = []
        for n in needs:
            if n.name in self._skills:
                s = self._skills[n.name]
                s.source = self.name # Ensure source is set
                found.append(s)
        return found

def test_priority_resolution_full_chain():
    """Verify learned > awesome > builtin"""
    
    # Setup skills matching same name but different description/source
    skill_name = "conflict-skill"
    
    s_learned = Skill(name=skill_name, description="From Learned", source="learned")
    s_awesome = Skill(name=skill_name, description="From Awesome", source="awesome")
    s_builtin = Skill(name=skill_name, description="From Builtin", source="builtin")
    
    # Config priority: learned(3) > awesome(2) > builtin(1)
    source_learned = MockSource("learned", 3, {skill_name: s_learned})
    source_awesome = MockSource("awesome", 2, {skill_name: s_awesome})
    source_builtin = MockSource("builtin", 1, {skill_name: s_builtin})
    
    orch = SkillOrchestrator({})
    # Register in random order to prove sorting works
    orch.register_source(source_builtin)
    orch.register_source(source_learned)
    orch.register_source(source_awesome)
    
    # Verify sources are sorted correctly
    assert orch.sources[0].name == "learned"
    assert orch.sources[1].name == "awesome"
    assert orch.sources[2].name == "builtin"
    
    # Discover
    needs = [SkillNeed(type="test", name=skill_name, confidence=1.0)]
    
    # We bypass full orchestrate to test _discover and _match specifically or just run orchestrate with mock analyzer?
    # Let's mock analyzer to return our needs
    orch.analyzer = MagicMock()
    orch.analyzer.analyze.return_value = needs
    
    # Run
    # Orchestrator.orchestrate calls _discover_skills then _match_skills
    # We expect _match_skills to pick the first one (highest priority)
    
    result = orch.orchestrate({}, ".")
    
    assert len(result) == 1
    assert result[0].name == skill_name
    assert result[0].source == "learned"
    assert result[0].description == "From Learned"

def test_priority_resolution_partial():
    """Verify awesome > builtin (when learned missing)"""
    
    skill_name = "conflict-skill"
    s_awesome = Skill(name=skill_name, description="From Awesome", source="awesome")
    s_builtin = Skill(name=skill_name, description="From Builtin", source="builtin")
    
    # Config priority: learned(3) > awesome(2) > builtin(1)
    source_awesome = MockSource("awesome", 2, {skill_name: s_awesome})
    source_builtin = MockSource("builtin", 1, {skill_name: s_builtin})
    
    orch = SkillOrchestrator({})
    orch.register_source(source_builtin)
    orch.register_source(source_awesome)
    
    orch.analyzer = MagicMock()
    orch.analyzer.analyze.return_value = [SkillNeed(type="test", name=skill_name, confidence=1.0)]
    
    result = orch.orchestrate({}, ".")
    
    assert len(result) == 1
    assert result[0].source == "awesome"

def test_priority_resolution_numeric_check():
    """Verify standard config logic produces correct numeric priorities"""
    
    # Preference order matching typical config
    prefs = ["learned", "awesome", "builtin"]
    
    # Logic extracted from source classes
    def get_prio(name, order):
        if name in order:
            return len(order) - order.index(name)
        return 0
        
    p_learned = get_prio("learned", prefs)
    p_awesome = get_prio("awesome", prefs)
    p_builtin = get_prio("builtin", prefs)
    
    assert p_learned == 3 
    assert p_awesome == 2 
    assert p_builtin == 1 
    
    assert p_learned > p_awesome > p_builtin
