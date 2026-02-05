"""Project type detection with caching"""
from pathlib import Path
from typing import Dict, List, Tuple, Any
from functools import lru_cache
import re

@lru_cache(maxsize=128)
def detect_project_type(
    project_name: str,
    tech_stack: Tuple[str, ...],  # Tuple for hashability
    readme_hash: int,  # Hash of README content for cache invalidation
    project_path: str
) -> Dict[str, Any]:
    """
    Detect project type from metadata.
    
    Cached for performance - same inputs return cached result.
    
    Args:
        project_name: Normalized project name
        tech_stack: Tuple of detected technologies
        readme_hash: Hash of README content for cache invalidation
        project_path: Path to project directory
        
    Returns:
        Dict with: primary_type, secondary_types, confidence, all_scores
    """
    scores = _initialize_scores()
    
    # Load README content from hash (not cached directly to save memory)
    readme_content = _load_readme_content(project_path)
    
    # Run detection algorithms
    _detect_agent_signals(scores, tech_stack, readme_content)
    _detect_ml_pipeline_signals(scores, tech_stack, readme_content)
    _detect_web_app_signals(scores, tech_stack, project_path, readme_content)
    _detect_cli_tool_signals(scores, tech_stack, readme_content, project_path)
    _detect_library_signals(scores, project_path, readme_content)
    _detect_generator_signals(scores, project_name, readme_content, project_path)
    
    # Apply penalties for hybrid projects
    _apply_hybrid_penalties(scores)
    
    return _calculate_final_scores(scores)


def _initialize_scores() -> Dict[str, float]:
    """Initialize score dictionary."""
    return {
        'agent': 0.0,
        'ml_pipeline': 0.0,
        'web_app': 0.0,
        'cli_tool': 0.0,
        'library': 0.0,
        'generator': 0.0
    }


def _detect_agent_signals(
    scores: Dict[str, float],
    tech_stack: Tuple[str, ...],
    readme: str
) -> None:
    """Detect AI agent project signals."""
    llm_providers = {'gemini', 'openai', 'anthropic', 'claude', 'gpt', 'langchain'}
    agent_keywords = {
        'agent', 'llm', 'autonomous', 'orchestration', 
        'workflow', 'intelligence', 'semantic search', 'ai-powered'
    }
    
    # LLM provider detection (strong signal)
    if any(llm in tech_stack for llm in llm_providers):
        scores['agent'] += 0.5
    
    # Agent keywords in README
    readme_lower = readme.lower()
    keyword_count = sum(1 for kw in agent_keywords if kw in readme_lower)
    scores['agent'] += min(keyword_count * 0.15, 0.5)


def _detect_ml_pipeline_signals(
    scores: Dict[str, float],
    tech_stack: Tuple[str, ...],
    readme: str
) -> None:
    """Detect ML/data pipeline signals."""
    ml_frameworks = {'pytorch', 'torch', 'tensorflow', 'sklearn', 'transformers', 'pandas'}
    video_tools = {'ffmpeg', 'opencv', 'pillow', 'moviepy'}
    ml_keywords = {
        'model', 'train', 'dataset', 'inference', 'pipeline',
        'video', 'frame', 'segment', 'media', 'broadcast', 'accuracy'
    }
    
    # ML frameworks (strong signal)
    if any(fw in tech_stack for fw in ml_frameworks):
        scores['ml_pipeline'] += 0.5
    
    # Video processing tools
    if any(tool in tech_stack for tool in video_tools):
        scores['ml_pipeline'] += 0.4
    
    # ML keywords
    readme_lower = readme.lower()
    keyword_count = sum(1 for kw in ml_keywords if kw in readme_lower)
    scores['ml_pipeline'] += min(keyword_count * 0.1, 0.4)


def _detect_web_app_signals(
    scores: Dict[str, float],
    tech_stack: Tuple[str, ...],
    project_path: str,
    readme: str
) -> None:
    """Detect web application signals."""
    web_frameworks = {'fastapi', 'flask', 'django', 'react', 'vue', 'angular', 'nextjs', 'svelte'}
    web_keywords = {'server', 'port', 'localhost', 'http', 'api'}
    
    # Web frameworks
    if any(fw in tech_stack for fw in web_frameworks):
        scores['web_app'] += 0.5
    
    # API directory structure
    if any(Path(project_path).glob('**/api/**')) or any(Path(project_path).glob('**/routers/**')):
        scores['web_app'] += 0.3
    
    readme_lower = readme.lower()
    if any(kw in readme_lower for kw in web_keywords):
        scores['web_app'] += 0.2


def _detect_cli_tool_signals(
    scores: Dict[str, float],
    tech_stack: Tuple[str, ...],
    readme: str,
    project_path: str
) -> None:
    """Detect CLI tool signals."""
    cli_libs = {'click', 'argparse', 'typer', 'fire'}
    cli_keywords = {'command', 'cli', 'terminal', 'usage:'}
    
    # CLI libraries (strong signal)
    if any(lib in tech_stack for lib in cli_libs):
        scores['cli_tool'] += 0.5
    
    # main.py without API structure
    has_main = Path(project_path, 'main.py').exists()
    has_api = any(Path(project_path).glob('**/api/**'))
    if has_main and not has_api:
        scores['cli_tool'] += 0.3
    
    # CLI keywords
    readme_lower = readme.lower()
    if any(kw in readme_lower for kw in cli_keywords):
        scores['cli_tool'] += 0.2


def _detect_library_signals(
    scores: Dict[str, float],
    project_path: str,
    readme: str
) -> None:
    """Detect library/package signals."""
    has_setup = Path(project_path, 'setup.py').exists()
    has_pyproject = Path(project_path, 'pyproject.toml').exists()
    has_main = Path(project_path, 'main.py').exists()
    
    if (has_setup or has_pyproject) and not has_main:
        scores['library'] += 0.4
        
    readme_lower = readme.lower()
    if any(kw in readme_lower for kw in ['import', 'package', 'library', 'pip install']):
        scores['library'] += 0.3


def _detect_generator_signals(
    scores: Dict[str, float],
    project_name: str,
    readme: str,
    project_path: str
) -> None:
    """Detect generator/scaffolding tool signals."""
    generator_keywords = {'generate', 'template', 'scaffold', 'boilerplate', 'create-'}
    
    # Project name
    if 'generator' in project_name or 'template' in project_name:
        scores['generator'] += 0.3
    
    # Templates directory
    if any(Path(project_path).glob('**/templates/**')):
        scores['generator'] += 0.3
    
    # Generator keywords
    readme_lower = readme.lower()
    keyword_count = sum(1 for kw in generator_keywords if kw in readme_lower)
    scores['generator'] += min(keyword_count * 0.15, 0.4)


def _apply_hybrid_penalties(scores: Dict[str, float]) -> None:
    """Penalize web_app if strong AI/ML signals present."""
    if scores['agent'] > 0.6 or scores['ml_pipeline'] > 0.6:
        scores['web_app'] *= 0.6


def _calculate_final_scores(scores: Dict[str, float]) -> Dict[str, Any]:
    """Calculate primary/secondary types and confidence."""
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    primary_type, primary_score = sorted_scores[0]
    secondary_types = [
        k for k, v in sorted_scores[1:3] 
        if v > 0.3 and k != 'generator'  # Don't leak generator to other projects
    ]
    
    return {
        'primary_type': primary_type,
        'secondary_types': secondary_types,
        'confidence': min(primary_score, 1.0),
        'all_scores': scores
    }


def _load_readme_content(project_path: str) -> str:
    """Load README content (helper for caching)."""
    try:
        return Path(project_path, 'README.md').read_text(encoding='utf-8').lower()
    except:
        # Try finding case insensitive
        try:
             # Find any readme
             readmes = list(Path(project_path).glob('README.md')) or list(Path(project_path).glob('readme.md'))
             if readmes:
                 return readmes[0].read_text(encoding='utf-8').lower()
        except:
            pass
        return ""


# Public wrapper that handles caching conversion
def detect_project_type_from_data(project_data: Dict[str, Any], project_path: str) -> Dict[str, Any]:
    """
    Public interface for project type detection.
    Converts project_data to cacheable format.
    
    Backwards compatibility wrapper for detect_project_type call signature.
    In original code: detect_project_type(project_data, project_path)
    We rename our cached function to _detect_project_type_cached and expose 
    detect_project_type as this wrapper to minimize breaking changes.
    """
    return detect_project_type(
        project_name=project_data['name'],
        tech_stack=tuple(project_data.get('tech_stack', [])),  # Convert to tuple for hashing
        readme_hash=hash(project_data.get('raw_readme', '')),
        project_path=str(project_path)
    )
