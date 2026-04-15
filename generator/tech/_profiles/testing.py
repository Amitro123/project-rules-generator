"""Testing TechProfile entries."""

from typing import List

from generator.tech.profile import TechProfile

TESTING: List[TechProfile] = [
    TechProfile(
        name="pytest",
        display_name="pytest",
        category="testing",
        skill_name="pytest-testing",
        packages=["pytest"],
        readme_keywords=["pytest"],
        tools=["pytest", "coverage", "pytest-cov"],
        rules={
            "high": [
                "Use fixtures for test setup/teardown (don't repeat setup)",
                "Parametrize tests with @pytest.mark.parametrize",
                "Mock external dependencies (APIs, databases)",
            ],
            "medium": [
                "Organize tests in tests/ mirroring source structure",
                "Use conftest.py for shared fixtures",
                "Add docstrings explaining what each test validates",
            ],
            "low": [
                "Use pytest.raises() for exception testing",
                "Add markers (@pytest.mark.slow) for test categories",
            ],
        },
    ),
    TechProfile(
        name="jest",
        display_name="Jest",
        category="testing",
        skill_name="jest-testing",
        packages=["jest"],
        readme_keywords=["jest"],
    ),
]
