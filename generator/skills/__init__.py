"""generator.skills — skill subsystem (loader, matcher, renderer, etc).

Eagerly imports the moved submodules so that ``unittest.mock.patch`` can
target them by dotted path immediately, without callers having to
explicitly import them first. Several tests use patterns like
``patch("generator.skills.llm_skill_generator.LLMSkillGenerator....")``;
that pattern only resolves if ``llm_skill_generator`` is bound as an
attribute of the ``generator.skills`` package, which Python only does
when the submodule has been imported.
"""

from generator.skills import (  # noqa: F401 — re-exports for patch() target binding
    llm_skill_generator,
    manager,
    skill_content_renderer,
    skill_creator,
    skill_discovery,
    skill_doc_loader,
    skill_generator,
    skill_metadata_builder,
    skill_parser,
    skill_project_scanner,
    skill_templates,
    skill_tracker,
    tag_resolver,
)
