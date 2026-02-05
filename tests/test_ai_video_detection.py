"""Test detection for AI video projects like MediaLens"""
import pytest
from analyzer.project_type_detector import detect_project_type
from generator.skills_generator import generate_skills

def test_medialens_detection():
    """MediaLens should be detected as agent, not web_app"""
    
    mock_data = {
        'name': 'medialens-ai',
        'tech_stack': ['python', 'fastapi', 'react', 'ffmpeg', 'gemini'],
        'raw_readme': '''
        # MediaLens AI
        Turn broadcast content into searchable intelligence.
        
        Uses Gemini for semantic analysis and ffmpeg for video processing.
        ''',
        'description': 'Turn broadcast content into searchable intelligence'
    }
    
    # Mock detection
    result = detect_project_type(mock_data, '.')
    
    # DEBUG info in case of failure
    print(f"Scores: {result['all_scores']}")
    
    # Should detect as agent or ml_pipeline, NOT web_app
    assert result['primary_type'] in ['agent', 'ml_pipeline'], \
        f"Expected agent/ml_pipeline, got {result['primary_type']}"
    
    assert result['confidence'] > 0.6, \
        f"Low confidence: {result['confidence']}"
    
    # web_app should be secondary at best
    assert 'web_app' != result['primary_type']
    
    # Test generated content
    content = generate_skills(mock_data, {}, '.')
    
    # Must have specific skills
    assert "prompt-improver" in content or "model-performance-analyzer" in content
    assert "fastapi-security-auditor" in content # Tech specific
    
    # Must NOT have generator skills
    assert "readme-deep-analyzer" not in content

def test_video_ml_detection():
    """Project with strong video focus should be ML pipeline"""
    mock_data = {
        'name': 'video-process-pipeline',
        'tech_stack': ['python', 'pytorch', 'opencv', 'moviepy', 'numpy'],
        'raw_readme': 'A deep learning pipeline for video segmentation and frame extraction.',
        'description': 'Video AI'
    }
    
    result = detect_project_type(mock_data, '.')
    
    assert result['primary_type'] == 'ml_pipeline'
    assert result['all_scores']['ml_pipeline'] >= 1.0 # 0.5 (ML) + 0.4 (video libs) + 0.3 (video KWs)
