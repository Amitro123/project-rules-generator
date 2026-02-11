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
import json
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
    
    def __init__(self, provider: str = 'groq', api_key: Optional[str] = None,
                 config: Optional[AnalyzerConfig] = None,
                 allowed_base_path: Optional[Path] = None,
                 client=None):
        """Initialize analyzer with AI client.
        
        Args:
            provider: AI provider ('gemini' or 'groq')
            api_key: Optional API key (uses env var if not provided)
            config: Optional configuration (uses defaults if not provided)
            allowed_base_path: Base path for file operations (security)
            client: Optional pre-configured AI client (for testing)
        """
        self.client = client or create_ai_client(provider=provider, api_key=api_key)
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

            # Get AI analysis with system message for structured output
            response = self.client.generate(
                prompt,
                temperature=self.config.ai_temperature,
                max_tokens=self.config.ai_max_tokens,
                system_message=self.ANALYSIS_SYSTEM_PROMPT
            )

            if response:
                breakdown, suggestions = self._parse_analysis_response(response)
                if breakdown is not None:
                    logger.debug(f"AI analysis successful for {filepath}")
        except (AIClientError, TimeoutError, ValueError, RuntimeError) as e:
            # AI unavailable or failed, will use heuristic below
            logger.warning(f"AI analysis failed for {filepath}: {e}, using heuristic")
        
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
    
    ANALYSIS_SYSTEM_PROMPT = (
        "You are a documentation quality analyzer. "
        "You MUST respond with ONLY valid JSON, no markdown, no explanation. "
        "JSON schema: {\"scores\":{\"structure\":int,\"clarity\":int,"
        "\"project_grounding\":int,\"actionability\":int,\"consistency\":int},"
        "\"suggestions\":[\"string\",\"string\",\"string\"]}"
    )

    IMPROVEMENT_SYSTEM_PROMPT = (
        "You are a technical documentation writer. "
        "Rewrite the provided document to fix the listed quality issues. "
        "Output ONLY the improved markdown content. "
        "Do NOT include analysis scores, file paths, quality breakdowns, "
        "improvement guidelines, XML tags, or any meta-commentary. "
        "Start directly with the first markdown heading."
    )

    def _build_analysis_prompt(self, filepath: str, content: str, project_path: Optional[Path]) -> str:
        """Build prompt for AI analysis."""
        project_context = self._get_project_context(project_path)

        prompt = f"""Analyze this documentation file for quality. Score each criterion 0-20.

Criteria:
- structure: Headers, logical flow, no empty sections
- clarity: Precise language, no fluff, terms defined
- project_grounding: References actual files/tools/commands
- actionability: Clear how-to steps, concrete examples
- consistency: Terminology and format consistent throughout

File: {filepath}
Content:
{content[:self.config.max_content_length]}
{project_context}

Return JSON only: {{"scores":{{"structure":N,"clarity":N,"project_grounding":N,"actionability":N,"consistency":N}},"suggestions":["improvement1","improvement2","improvement3"]}}"""
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
    
    def _build_project_context(self, project_path: Optional[Path]) -> Optional[str]:
        """Build short project context string for improvement prompts.

        Returns a compact block with real file paths, CLI commands, and
        tech stack so the AI can reference them when improving content.
        """
        if not project_path:
            return None

        lines = []

        # Entry point
        if (project_path / "main.py").exists():
            lines.append("- Entry point: main.py")

        # Key directories
        for d in ("generator", "analyzer", "tests", "src"):
            if (project_path / d).is_dir():
                lines.append(f"- Module: {d}/")

        # CLI commands (from pyproject.toml or setup.py)
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                text = pyproject.read_text(encoding='utf-8')
                if "prg" in text:
                    lines.append("- CLI command: prg")
            except Exception:
                pass

        # Test command
        if (project_path / "tests").is_dir():
            lines.append("- Run tests: pytest tests/ -v")

        # README title (first line)
        readme = project_path / "README.md"
        if readme.exists():
            try:
                first_line = readme.read_text(encoding='utf-8').split('\n', 1)[0].strip('# \t')
                if first_line:
                    lines.append(f"- Project: {first_line}")
            except Exception:
                pass

        return '\n'.join(lines) if lines else None

    def _parse_analysis_response(self, response: str) -> tuple[Optional[QualityBreakdown], List[str]]:
        """Parse AI response into breakdown and suggestions.

        Tries JSON parsing first, falls back to regex extraction.
        Returns (None, []) if parsing fails entirely.
        """
        # Try JSON parsing first (preferred for Groq/Llama)
        try:
            # Strip markdown code fences if model wrapped JSON in them
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', response.strip())
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)
            data = json.loads(cleaned)

            scores = data.get('scores', {})
            clamp = lambda v: max(0, min(20, int(v)))
            breakdown = QualityBreakdown(
                structure=clamp(scores.get('structure', 10)),
                clarity=clamp(scores.get('clarity', 10)),
                project_grounding=clamp(scores.get('project_grounding', 10)),
                actionability=clamp(scores.get('actionability', 10)),
                consistency=clamp(scores.get('consistency', 10))
            )
            suggestions = [str(s) for s in data.get('suggestions', []) if s]
            logger.debug("Parsed analysis response as JSON")
            return breakdown, suggestions
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.debug("JSON parse failed, trying regex fallback")

        # Regex fallback for non-JSON responses
        structure = self._extract_score(response, "Structure")
        clarity = self._extract_score(response, "Clarity")
        project_grounding = self._extract_score(response, "Project Grounding")
        actionability = self._extract_score(response, "Actionability")
        consistency = self._extract_score(response, "Consistency")

        # Check if we actually found any real scores (not all defaults)
        scores_found = [structure, clarity, project_grounding, actionability, consistency]
        if all(s == 10 for s in scores_found):
            return None, []

        breakdown = QualityBreakdown(
            structure=structure,
            clarity=clarity,
            project_grounding=project_grounding,
            actionability=actionability,
            consistency=consistency
        )

        # Extract suggestions from various formats
        suggestions = []
        # Try **SUGGESTIONS:** section
        suggestion_section = re.search(r'\*\*SUGGESTIONS:\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)', response, re.DOTALL)
        if suggestion_section:
            lines = suggestion_section.group(1).strip().split('\n')
            for line in lines:
                match = re.match(r'^\d+\.\s*(.+)$', line.strip())
                if match:
                    suggestions.append(match.group(1))
        # Try bare numbered list if no section header found
        if not suggestions:
            for match in re.finditer(r'^\d+\.\s*(.+)$', response, re.MULTILINE):
                suggestions.append(match.group(1))
            # Deduplicate while preserving order
            suggestions = list(dict.fromkeys(suggestions))

        return breakdown, suggestions[:5]
    
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

        # Structure analysis (base: 18/20)
        structure_score = 18
        if not content.startswith('#'):
            structure_score -= 5
            suggestions.append("Add a main H1 header at the top")
        if content.count('\n## ') < 2:
            structure_score -= 3
            suggestions.append("Add more H2 section headers for better organization")
        if '\n\n\n\n' in content:
            structure_score -= 2
            suggestions.append("Remove excessive blank lines")

        # Clarity analysis (base: 18/20)
        clarity_score = 18
        if len(content) < 200:
            clarity_score -= 5
            suggestions.append("Content is too brief, add more details")
        if content.count('TODO') > 0 or content.count('FIXME') > 0:
            clarity_score -= 3
            suggestions.append("Remove TODO/FIXME placeholders")

        # Project grounding analysis (base: 16/20)
        grounding_score = 16
        if '.py' not in content and '.js' not in content and '.md' not in content:
            grounding_score -= 5
            suggestions.append("Reference specific project files")
        if '`' not in content:
            grounding_score -= 3
            suggestions.append("Use code formatting for technical terms")

        # Actionability analysis (base: 16/20)
        actionability_score = 16
        if content.count('```') < 2:
            actionability_score -= 4
            suggestions.append("Add code examples or command snippets")
        if not any(word in content.lower() for word in ['run', 'execute', 'create', 'update', 'install']):
            actionability_score -= 3
            suggestions.append("Add actionable verbs and instructions")

        # Consistency analysis (base: 17/20)
        consistency_score = 17
        
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
        # Import here to avoid circular dependency
        from generator.ai.prompts import get_improvement_prompt
        
        # Truncate content to match what the analysis prompt sees.
        # This ensures improvements target the scored portion rather than
        # fixing unscored sections while leaving scored problems intact.
        max_len = self.config.max_content_length
        truncated = content[:max_len] if len(content) > max_len else content

        # Build short project context so the AI can reference real files/commands
        project_ctx = self._build_project_context(project_path)

        prompt = get_improvement_prompt(
            filepath, truncated, breakdown, suggestions,
            project_context=project_ctx,
        )

        try:
            improved = self.client.generate(
                prompt,
                temperature=0.5,
                max_tokens=self.config.patch_max_tokens,
                system_message=self.IMPROVEMENT_SYSTEM_PROMPT,
            )

            improved = self._sanitize_patch(improved)

            # If the original content was truncated, append the remainder
            # so we don't silently drop the tail of the document.
            if len(content) > max_len:
                improved = improved.strip() + "\n\n" + content[max_len:]

            return improved.strip()
        except Exception as e:
            logger.warning(f"Failed to generate patch for {filepath}: {e}")
            # If AI fails, return original content
            return content

    # Patterns that indicate prompt leakage in AI output
    _LEAK_PATTERNS = [
        # Echoed prompt sections (old and new prompt formats)
        re.compile(r'^#{1,3}\s*Quality Analysis\b.*', re.MULTILINE),
        re.compile(r'^#{1,3}\s*Specific Issues to Fix\b.*', re.MULTILINE),
        re.compile(r'^#{1,3}\s*Improvement Guidelines\b.*', re.MULTILINE),
        re.compile(r'^#{1,3}\s*Your Task\b.*', re.MULTILINE),
        re.compile(r'^#{1,3}\s*Output Format\b.*', re.MULTILINE),
        re.compile(r'^#{1,3}\s*Documentation Improvement Task\b.*', re.MULTILINE),
        # Echoed delimiters / instructions
        re.compile(r'^</?document>\s*$', re.MULTILINE),
        re.compile(r'^Fix these issues \(current score:.*$', re.MULTILINE),
        re.compile(r'^Output the complete improved document.*$', re.MULTILINE),
        # Metadata lines
        re.compile(r'^\*\*File:\*\*\s*.+$', re.MULTILINE),
        re.compile(r'^Filename:\s*.+$', re.MULTILINE),
        # Preamble
        re.compile(r'^(?:Here\'s|Here is).+(?:improved|rewritten|updated).+:\s*$', re.MULTILINE | re.IGNORECASE),
        # Score markers that shouldn't appear in output
        re.compile(r'NEEDS IMPROVEMENT', re.IGNORECASE),
    ]

    # Section-level patterns: strip entire section until next heading or EOF
    _LEAK_SECTION_PATTERNS = [
        re.compile(r'#{1,3}\s*Quality Analysis\s*\(Score:.*?(?=\n#{1,3}\s|\Z)', re.DOTALL),
        re.compile(r'#{1,3}\s*Specific Issues to Fix.*?(?=\n#{1,3}\s|\Z)', re.DOTALL),
        re.compile(r'#{1,3}\s*Improvement Guidelines.*?(?=\n#{1,3}\s|\Z)', re.DOTALL),
        re.compile(r'#{1,3}\s*Your Task.*?(?=\n#{1,3}\s|\Z)', re.DOTALL),
        re.compile(r'#{1,3}\s*Output Format.*?(?=\n#{1,3}\s|\Z)', re.DOTALL),
        re.compile(r'#{1,3}\s*Structure Improvements.*?(?=\n#{1,3}\s|\Z)', re.DOTALL),
        re.compile(r'#{1,3}\s*Clarity Improvements.*?(?=\n#{1,3}\s|\Z)', re.DOTALL),
        re.compile(r'#{1,3}\s*Project Grounding Improvements.*?(?=\n#{1,3}\s|\Z)', re.DOTALL),
        re.compile(r'#{1,3}\s*Actionability Improvements.*?(?=\n#{1,3}\s|\Z)', re.DOTALL),
        re.compile(r'#{1,3}\s*Consistency Improvements.*?(?=\n#{1,3}\s|\Z)', re.DOTALL),
    ]

    def _sanitize_patch(self, text: str) -> str:
        """Remove prompt leakage and formatting artifacts from AI output.

        Applies multiple cleanup passes:
        1. Strip markdown code fences wrapping entire output
        2. Remove leaked section-level prompt content
        3. Remove individual leaked lines
        4. Collapse excessive blank lines
        """
        # 1. Remove wrapping code fences
        text = re.sub(r'^```(?:markdown)?\n', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n```\s*$', '', text)

        # 2. Remove full leaked sections (greedy match to next heading)
        for pattern in self._LEAK_SECTION_PATTERNS:
            text = pattern.sub('', text)

        # 3. Remove individual leaked lines
        for pattern in self._LEAK_PATTERNS:
            text = pattern.sub('', text)

        # 4. Collapse excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text
