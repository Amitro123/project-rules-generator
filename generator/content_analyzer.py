"""AI-powered content analyzer for .clinerules files.

Analyzes generated documentation for quality across 5 criteria:
- Structure: Headers, logical flow, no empty sections
- Clarity: Precise language, no fluff
- Project Grounding: References actual files/tools/commands
- Actionability: "How to act" not just theory
- Consistency: Terminology, format matches project
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import re
import logging

from generator.ai.ai_client import create_ai_client
from generator.config import AnalyzerConfig
from generator.exceptions import AIClientError, ValidationError, SecurityError, FileOperationError

logger = logging.getLogger(__name__)


@dataclass
class QualityBreakdown:
    """Breakdown of quality scores by criterion."""
    structure: int  # 0-20
    clarity: int  # 0-20
    project_grounding: int  # 0-20
    actionability: int  # 0-20
    consistency: int  # 0-20
    
    @property
    def total(self) -> int:
        """Calculate total score."""
        return (
            self.structure + 
            self.clarity + 
            self.project_grounding + 
            self.actionability + 
            self.consistency
        )


@dataclass
class QualityReport:
    """Quality analysis report for a content file."""
    filepath: str
    score: int  # 0-100
    breakdown: QualityBreakdown
    suggestions: List[str]
    patch: Optional[str] = None  # Generated patch if score < 85
    
    @property
    def status(self) -> str:
        """Get status emoji based on score."""
        if self.score >= 90:
            return "✅ Excellent"
        elif self.score >= 85:
            return "✅ Good"
        elif self.score >= 70:
            return "⚠️  Needs improvement"
        else:
            return "❌ Poor quality"


class ContentAnalyzer:
    """Analyze .clinerules content for quality and generate improvements."""
    
    def __init__(self, provider: str = 'gemini', api_key: Optional[str] = None,
                 config: Optional[AnalyzerConfig] = None,
                 allowed_base_path: Optional[Path] = None):
        """Initialize analyzer with AI client.
        
        Args:
            provider: AI provider ('gemini' or 'groq')
            api_key: Optional API key (uses env var if not provided)
            config: Optional configuration (uses defaults if not provided)
            allowed_base_path: Base path for file operations (security)
        """
        self.client = create_ai_client(provider=provider, api_key=api_key)
        self.config = config or AnalyzerConfig()
        self.allowed_base_path = allowed_base_path.resolve() if allowed_base_path else Path.cwd().resolve()
        logger.info(f"ContentAnalyzer initialized with provider={provider}")
    
    def analyze(self, filepath: str, content: str, project_path: Optional[Path] = None) -> QualityReport:
        """Analyze content quality and generate report.
        
        Args:
            filepath: Path to the file being analyzed
            content: File content to analyze
            project_path: Optional project root for context
            
        Returns:
            QualityReport with scores, suggestions, and optional patch
            
        Raises:
            ValidationError: If filepath or content is invalid
        """
        # Input validation
        if not filepath:
            raise ValidationError("filepath cannot be empty")
        if not content or not content.strip():
            raise ValidationError("content cannot be empty")
        if len(content) > 1_000_000:  # 1MB limit
            raise ValidationError("content too large (max 1MB)")
        
        logger.debug(f"Analyzing {filepath} ({len(content)} bytes)")
        
        # Try AI analysis first, fall back to heuristic if unavailable
        breakdown = None
        suggestions = []
        
        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(filepath, content, project_path)
            
            # Get AI analysis
            response = self.client.generate(
                prompt,
                temperature=self.config.ai_temperature,
                max_tokens=self.config.ai_max_tokens
            )
            
            # Only use AI response if it contains valid scores
            if response and 'Structure:' in response:
                breakdown, suggestions = self._parse_analysis_response(response)
                logger.debug(f"AI analysis successful for {filepath}")
        except (AIClientError, TimeoutError, ValueError) as e:
            # AI unavailable or failed, will use heuristic below
            logger.warning(f"AI analysis failed for {filepath}: {e}, using heuristic")
            pass
        
        # Use heuristic analysis if AI failed or returned invalid data
        if breakdown is None or breakdown.total == self.config.total_default_score:
            logger.info(f"Using heuristic analysis for {filepath}")
            breakdown, suggestions = self._heuristic_analysis(filepath, content)
        
        score = breakdown.total
        
        # Generate patch if score is low
        patch = None
        if score < self.config.low_score_threshold:
            logger.info(f"Generating patch for {filepath} (score={score})")
            patch = self._generate_patch(filepath, content, breakdown, suggestions, project_path)
        
        return QualityReport(
            filepath=filepath,
            score=score,
            breakdown=breakdown,
            suggestions=suggestions,
            patch=patch
        )
    
    def apply_fix(self, filepath: Path, patch: str) -> None:
        """Apply generated patch to file.
        
        Args:
            filepath: Path to file to fix
            patch: Patch content to apply
            
        Raises:
            SecurityError: If path is outside allowed directory
            FileOperationError: If file write fails
        """
        # Validate path is within allowed directory
        filepath = filepath.resolve()
        try:
            filepath.relative_to(self.allowed_base_path)
        except ValueError:
            raise SecurityError(
                f"Path {filepath} is outside allowed directory {self.allowed_base_path}"
            )
        
        try:
            filepath.write_text(patch, encoding='utf-8')
            logger.info(f"Applied fix to {filepath}")
        except Exception as e:
            raise FileOperationError(f"Failed to write to {filepath}: {e}")
    
    def _build_analysis_prompt(self, filepath: str, content: str, project_path: Optional[Path]) -> str:
        """Build prompt for AI analysis."""
        project_context = self._get_project_context(project_path)
        scoring_criteria = self._get_scoring_criteria_text()
        
        prompt = f"""# Content Quality Analysis

Analyze this AI agent documentation file for quality across 5 criteria.

**File:** {filepath}

**Content:**
```markdown
{content[:3000]}
```
{project_context}

{scoring_criteria}

## Your Task

Provide scores and specific suggestions in this format:

**SCORES:**
Structure: [0-20]
Clarity: [0-20]
Project Grounding: [0-20]
Actionability: [0-20]
Consistency: [0-20]

**SUGGESTIONS:**
1. [Specific improvement for lowest-scoring criterion]
2. [Another specific improvement]
3. [Another specific improvement]

Be critical but constructive. Focus on actionable improvements.
"""
        return prompt
    
    def _get_project_context(self, project_path: Optional[Path]) -> str:
        """Extract project context if available."""
        if not project_path:
            return ""
        
        readme_path = project_path / "README.md"
        if readme_path.exists():
            try:
                readme_content = readme_path.read_text(encoding='utf-8')[:1000]
                return f"\n\n**Project README (excerpt):**\n{readme_content}"
            except Exception as e:
                logger.warning(f"Failed to read README: {e}")
        return ""
    
    def _get_scoring_criteria_text(self) -> str:
        """Return scoring criteria as formatted text."""
        return """## Scoring Criteria (20 points each, total 100)

### 1. Structure (0-20)
- Proper headers (H1, H2, H3 hierarchy)
- Logical flow and organization
- No empty sections
- Clear table of contents if needed

### 2. Clarity (0-20)
- Precise, concise language
- No fluff or vague statements
- Technical terms defined
- Examples are clear

### 3. Project Grounding (0-20)
- References actual files from the project
- Mentions specific tools/commands used
- Includes real paths, not placeholders
- Context-aware recommendations

### 4. Actionability (0-20)
- Clear "how to" instructions
- Specific steps, not just theory
- Concrete examples
- Executable commands

### 5. Consistency (0-20)
- Terminology matches project conventions
- Format consistent throughout
- Style matches other documentation
- No contradictions"""
    
    def _parse_analysis_response(self, response: str) -> tuple[QualityBreakdown, List[str]]:
        """Parse AI response into breakdown and suggestions."""
        
        # Extract scores
        structure = self._extract_score(response, "Structure")
        clarity = self._extract_score(response, "Clarity")
        project_grounding = self._extract_score(response, "Project Grounding")
        actionability = self._extract_score(response, "Actionability")
        consistency = self._extract_score(response, "Consistency")
        
        breakdown = QualityBreakdown(
            structure=structure,
            clarity=clarity,
            project_grounding=project_grounding,
            actionability=actionability,
            consistency=consistency
        )
        
        # Extract suggestions
        suggestions = []
        suggestion_section = re.search(r'\*\*SUGGESTIONS:\*\*(.*?)(?:\n\n|\Z)', response, re.DOTALL)
        if suggestion_section:
            lines = suggestion_section.group(1).strip().split('\n')
            for line in lines:
                # Match numbered suggestions like "1. Fix headers"
                match = re.match(r'^\d+\.\s*(.+)$', line.strip())
                if match:
                    suggestions.append(match.group(1))
        
        return breakdown, suggestions
    
    def _extract_score(self, response: str, criterion: str) -> int:
        """Extract score for a specific criterion from AI response."""
        pattern = rf'{criterion}:\s*(-?\d+)'  # Allow negative numbers
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            return max(0, min(20, score))  # Clamp to 0-20
        return 10  # Default middle score if not found
    
    def _heuristic_analysis(self, filepath: str, content: str) -> tuple[QualityBreakdown, List[str]]:
        """Fallback heuristic analysis when AI is unavailable."""
        
        suggestions = []
        
        # Structure analysis
        structure_score = 15
        if not content.startswith('#'):
            structure_score -= 5
            suggestions.append("Add a main H1 header at the top")
        if content.count('\n## ') < 2:
            structure_score -= 3
            suggestions.append("Add more H2 section headers for better organization")
        if '\n\n\n\n' in content:
            structure_score -= 2
            suggestions.append("Remove excessive blank lines")
        
        # Clarity analysis
        clarity_score = 15
        if len(content) < 200:
            clarity_score -= 5
            suggestions.append("Content is too brief, add more details")
        if content.count('TODO') > 0 or content.count('FIXME') > 0:
            clarity_score -= 3
            suggestions.append("Remove TODO/FIXME placeholders")
        
        # Project grounding analysis
        grounding_score = 12
        if '.py' not in content and '.js' not in content and '.md' not in content:
            grounding_score -= 5
            suggestions.append("Reference specific project files")
        if '`' not in content:
            grounding_score -= 3
            suggestions.append("Use code formatting for technical terms")
        
        # Actionability analysis
        actionability_score = 13
        if content.count('```') < 2:
            actionability_score -= 4
            suggestions.append("Add code examples or command snippets")
        if not any(word in content.lower() for word in ['run', 'execute', 'create', 'update', 'install']):
            actionability_score -= 3
            suggestions.append("Add actionable verbs and instructions")
        
        # Consistency analysis
        consistency_score = 14
        
        breakdown = QualityBreakdown(
            structure=structure_score,
            clarity=clarity_score,
            project_grounding=grounding_score,
            actionability=actionability_score,
            consistency=consistency_score
        )
        
        return breakdown, suggestions[:5]  # Limit to top 5 suggestions
    
    def _generate_patch(
        self, 
        filepath: str, 
        content: str, 
        breakdown: QualityBreakdown,
        suggestions: List[str],
        project_path: Optional[Path]
    ) -> str:
        """Generate improved version of content.
        
        Args:
            filepath: Path to file
            content: Original content
            breakdown: Quality breakdown
            suggestions: List of suggestions
            project_path: Optional project root
            
        Returns:
            Improved content as patch
        """
        # Build improvement prompt
        suggestions_text = '\n'.join(f"{i+1}. {s}" for i, s in enumerate(suggestions))
        
        prompt = f"""# Improve Documentation

**File:** {filepath}

**Current Content:**
```markdown
{content}
```

**Quality Issues (Score: {breakdown.total}/100):**
- Structure: {breakdown.structure}/20
- Clarity: {breakdown.clarity}/20
- Project Grounding: {breakdown.project_grounding}/20
- Actionability: {breakdown.actionability}/20
- Consistency: {breakdown.consistency}/20

**Specific Improvements Needed:**
{suggestions_text}

## Your Task

Rewrite the content to address ALL the issues above. Focus on:
1. Fixing the lowest-scoring criteria first
2. Keeping the original intent and information
3. Making it more actionable and specific
4. Adding concrete examples where missing

Return ONLY the improved markdown content, no explanations.
"""
        
        try:
            improved = self.client.generate(prompt, temperature=0.5, max_tokens=3000)
            # Clean up the response (remove markdown code fences if present)
            improved = re.sub(r'^```markdown\n', '', improved)
            improved = re.sub(r'\n```$', '', improved)
            return improved.strip()
        except Exception:
            # If AI fails, return original content
            return content
