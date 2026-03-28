"""Base class for all PRG artifact generators.

Strategic-depth contract enforced here:
  - Pain-first: open with the reader's broken state, not the artifact's features.
  - Why-before-how: reasoning precedes every rule, step, or task.
  - Skip-consequence: plans surface what breaks when a task is omitted.

Subclasses keep their own __init__.  The base contributes:
  - Shared LLM prompt fragments (_PAIN_FIRST_PREAMBLE, _WHY_RULE_FORMAT,
    _SKIP_CONSEQUENCE_FORMAT)
  - format_rule_with_why() — annotates any rule string with its WHY clause
  - validate_depth()       — runs the strategic-depth quality gate
  - Abstract _build_prompt() — every subclass must embed the preamble
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from generator.utils.quality_checker import QualityReport


class ArtifactGenerator(ABC):
    """Abstract base for CoworkRulesCreator, TaskDecomposer, SkillGenerator.

    No __init__ is defined here — subclasses keep whatever constructor they
    already have and call super().__init__() only if they choose to.
    """

    # ------------------------------------------------------------------ #
    #  Shared prompt fragments                                             #
    # ------------------------------------------------------------------ #

    _PAIN_FIRST_PREAMBLE: str = (
        "STRATEGIC DEPTH — apply to every item you generate:\n"
        "1. Pain before prescription: describe what BREAKS or FAILS without this "
        "rule/step/task before stating what to do.\n"
        "2. Why before how: write one sentence of reasoning before every command or action.\n"
        "3. Never open with 'This rule/plan does X'. "
        "Open with the developer's broken state.\n"
    )

    _WHY_RULE_FORMAT: str = (
        "Format every rule on one line exactly like this:\n"
        "DO: <imperative rule> | WHY: <one sentence — what breaks without it>\n"
        "DONT: <anti-pattern> | WHY: <one sentence — what failure mode this causes>\n"
        "No extra markdown, no blank lines between rules.\n"
    )

    _SKIP_CONSEQUENCE_FORMAT: str = (
        "For every subtask include a SkipConsequence line:\n"
        "SkipConsequence: <one sentence — what is blocked or broken if this task is omitted>\n"
    )

    # ------------------------------------------------------------------ #
    #  Shared utilities                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def format_rule_with_why(rule_text: str, why: str) -> str:
        """Append a WHY clause to a rule string.

        Returns the rule unchanged if why is empty or already annotated.

        Example::

            format_rule_with_why(
                "Use async/await for I/O operations",
                "blocking the event loop stalls all concurrent requests",
            )
            # → "Use async/await for I/O operations — blocking the event loop
            #    stalls all concurrent requests."
        """
        rule_text = rule_text.strip().rstrip(".")
        why = why.strip().rstrip(".")
        if not why or " — " in rule_text:
            return rule_text
        return f"{rule_text} — {why}."

    def validate_depth(self, content: str) -> "QualityReport":
        """Run the strategic-depth quality gate on generated content.

        Delegates to quality_checker.validate_quality(), which includes
        _check_strategic_depth() (pain-first Purpose, why-reasoning in steps).
        """
        from generator.utils.quality_checker import validate_quality

        return validate_quality(content)

    # ------------------------------------------------------------------ #
    #  Contract                                                            #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def _build_prompt(self, *args, **kwargs) -> str:
        """Build the LLM prompt for this generator.

        Implementations MUST embed ``_PAIN_FIRST_PREAMBLE`` and the
        appropriate format fragment:
        - Rules generators  → ``_WHY_RULE_FORMAT``
        - Plan generators   → ``_SKIP_CONSEQUENCE_FORMAT``
        - Skill generators  → delegate to ``skill_generation.build_skill_prompt``
          (already contains rules 9-11 added in the skills refactor)
        """
