from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field, EmailStr

class LLMConfig(BaseModel):
    enabled: bool = False
    api_key: Optional[str] = None
    provider: Literal["anthropic", "gemini"] = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"

class GitConfig(BaseModel):
    auto_commit: bool = True
    commit_message: str = "Auto-generated rules and skills"
    commit_user_name: str = "Project Rules Generator"
    commit_user_email: str = "rules@generator.local"

class GenerationConfig(BaseModel):
    output_format: Literal["markdown", "json", "yaml"] = "markdown"
    include_examples: bool = True
    verbose: bool = True
    max_feature_count: int = Field(default=5, ge=1, le=20)
    max_description_length: int = Field(default=200, ge=50, le=1000)

class PacksConfig(BaseModel):
    enabled: bool = True
    sources: List[str] = Field(default_factory=list)


class SkillSourceConfig(BaseModel):
    enabled: bool = True
    path: Optional[str] = None
    auto_save: bool = False

class SkillSourcesConfig(BaseModel):
    builtin: SkillSourceConfig = Field(default_factory=lambda: SkillSourceConfig(enabled=True, path="templates/skills"))
    learned: SkillSourceConfig = Field(default_factory=lambda: SkillSourceConfig(enabled=True, path="~/.project-rules-generator/learned_skills", auto_save=True))
    awesome: SkillSourceConfig = Field(default_factory=lambda: SkillSourceConfig(enabled=False, path=""))
    preference_order: List[str] = Field(default_factory=lambda: ["learned", "awesome", "builtin"])

class RootConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    packs: PacksConfig = Field(default_factory=PacksConfig)
    skill_sources: SkillSourcesConfig = Field(default_factory=SkillSourcesConfig)

def validate_config(config_dict: Dict) -> RootConfig:
    """Validate and normalize configuration dictionary."""
    return RootConfig(**config_dict)
