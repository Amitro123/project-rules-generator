"""generator.rules_sections — section-builder helpers package.

Re-exports all public helpers so existing import sites continue to work:
    from generator.rules_sections import _build_test_section
"""

from generator.rules_sections.do_dont import _build_do_rules, _build_dont_rules
from generator.rules_sections.structure import (
    _build_context_strategy,
    _build_dep_section,
    _build_file_structure,
)
from generator.rules_sections.templates import _generate_basic_rules, _generate_enhanced_rules
from generator.rules_sections.testing import _build_test_section
from generator.rules_sections.workflows import _build_workflow_section, _sanitize_readme_section

__all__ = [
    "_build_context_strategy",
    "_build_dep_section",
    "_build_do_rules",
    "_build_dont_rules",
    "_build_file_structure",
    "_build_test_section",
    "_build_workflow_section",
    "_generate_basic_rules",
    "_generate_enhanced_rules",
    "_sanitize_readme_section",
]
