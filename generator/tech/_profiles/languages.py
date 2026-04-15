"""Language detection-only TechProfile entries (no skill generated)."""

from typing import List

from generator.tech.profile import TechProfile

LANGUAGES: List[TechProfile] = [
    TechProfile(
        name="python",
        display_name="Python",
        category="language",
        skill_name="",
        packages=[],
        readme_keywords=["python"],
    ),
    TechProfile(
        name="typescript",
        display_name="TypeScript",
        category="language",
        skill_name="",
        packages=[],
        readme_keywords=["typescript"],
    ),
    TechProfile(
        name="javascript",
        display_name="JavaScript",
        category="language",
        skill_name="",
        packages=[],
        readme_keywords=["javascript", "node.js", "nodejs"],
    ),
    TechProfile(
        name="go",
        display_name="Go",
        category="language",
        skill_name="",
        packages=[],
        readme_keywords=["golang", "go lang"],
    ),
    TechProfile(
        name="rust",
        display_name="Rust",
        category="language",
        skill_name="",
        packages=[],
        readme_keywords=["rust", "rustlang", "cargo"],
    ),
]
