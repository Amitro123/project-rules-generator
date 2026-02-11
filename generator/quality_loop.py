"""Quality feedback loop for iterative content improvement.

Implements an iterative improvement system that automatically regenerates
low-quality content with AI feedback until achieving target scores.
"""

import logging
from pathlib import Path
from typing import Optional

from generator.content_analyzer import ContentAnalyzer, QualityReport

logger = logging.getLogger(__name__)


def improve_with_feedback(
    filepath: Path,
    analyzer: ContentAnalyzer,
    target_score: int = 85,
    max_iterations: int = 3,
    project_path: Optional[Path] = None,
    verbose: bool = False
) -> QualityReport:
    """Iteratively improve content until target score is reached.
    
    This function implements a feedback loop that:
    1. Analyzes current content quality
    2. If score < target, generates improved version
    3. Applies the improvement and re-analyzes
    4. Repeats until target reached or max iterations exceeded
    
    Args:
        filepath: Path to file to improve
        analyzer: ContentAnalyzer instance to use
        target_score: Target quality score (default: 85)
        max_iterations: Maximum improvement iterations (default: 3)
        project_path: Optional project root for context
        verbose: Whether to print progress messages
        
    Returns:
        QualityReport with final score (>= target_score or best attempt)
        
    Raises:
        FileNotFoundError: If filepath doesn't exist
        ValueError: If target_score or max_iterations are invalid
    """
    # Input validation
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    if not 0 <= target_score <= 100:
        raise ValueError(f"target_score must be 0-100, got {target_score}")
    if max_iterations < 1:
        raise ValueError(f"max_iterations must be >= 1, got {max_iterations}")
    
    # Read initial content
    content = filepath.read_text(encoding='utf-8')
    
    # Track best attempt in case we don't reach target
    best_report = None
    best_score = 0
    
    for iteration in range(1, max_iterations + 1):
        # Analyze current content
        report = analyzer.analyze(
            str(filepath.relative_to(filepath.parent.parent) if filepath.parent.parent.exists() else filepath.name),
            content,
            project_path=project_path
        )
        
        # Update best attempt
        if report.score > best_score:
            best_score = report.score
            best_report = report
        
        if verbose:
            logger.info(f"  Iteration {iteration}/{max_iterations}: {report.score}/100")
        
        # Check if target reached
        if report.score >= target_score:
            if verbose:
                logger.info(f"  ✅ Target reached ({report.score}/100)")
            
            # Apply final fix if we have a patch
            if report.patch:
                analyzer.apply_fix(filepath, report.patch)
                # Re-analyze to get final report
                content = filepath.read_text(encoding='utf-8')
                final_report = analyzer.analyze(
                    str(filepath.relative_to(filepath.parent.parent) if filepath.parent.parent.exists() else filepath.name),
                    content,
                    project_path=project_path
                )
                return final_report
            
            return report
        
        # Generate improvement if we haven't reached target
        if not report.patch:
            # No patch generated (shouldn't happen for low scores, but handle it)
            logger.warning(f"No patch generated for {filepath} (score={report.score})")
            break
        
        # Apply the improvement
        try:
            analyzer.apply_fix(filepath, report.patch)
            # Read updated content for next iteration
            content = filepath.read_text(encoding='utf-8')
            
            if verbose:
                logger.info(f"  Applied improvement patch")
                
        except Exception as e:
            logger.error(f"Failed to apply patch at iteration {iteration}: {e}")
            break
    
    # Max iterations reached or error occurred
    if verbose:
        if best_score < target_score:
            logger.warning(
                f"  ⚠️  Target not reached. Best score: {best_score}/100 "
                f"(target: {target_score})"
            )
        else:
            logger.info(f"  ✅ Completed in {max_iterations} iterations")
    
    return best_report or report


def batch_improve_with_feedback(
    filepaths: list[Path],
    analyzer: ContentAnalyzer,
    target_score: int = 85,
    max_iterations: int = 3,
    project_path: Optional[Path] = None,
    verbose: bool = False
) -> dict[Path, QualityReport]:
    """Improve multiple files with feedback loop.
    
    Args:
        filepaths: List of file paths to improve
        analyzer: ContentAnalyzer instance to use
        target_score: Target quality score (default: 85)
        max_iterations: Maximum improvement iterations per file (default: 3)
        project_path: Optional project root for context
        verbose: Whether to print progress messages
        
    Returns:
        Dictionary mapping filepath to final QualityReport
    """
    results = {}
    
    for filepath in filepaths:
        if verbose:
            logger.info(f"\nImproving {filepath.name}...")
        
        try:
            report = improve_with_feedback(
                filepath,
                analyzer,
                target_score=target_score,
                max_iterations=max_iterations,
                project_path=project_path,
                verbose=verbose
            )
            results[filepath] = report
            
            if verbose:
                logger.info(f"  Final score: {report.score}/100")
                
        except Exception as e:
            logger.error(f"Failed to improve {filepath}: {e}")
            # Continue with other files
            
    return results
