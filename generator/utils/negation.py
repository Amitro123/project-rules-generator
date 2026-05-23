"""Negation-aware keyword matching for README/prose text.

Shared between ``generator/analyzers/readme_parser.py`` and
``generator/utils/tech_detector.py`` so the negation policy lives in
exactly one place. Without this, each README scanner had to re-implement
the same guard, and the most-recently-touched scanner would silently
diverge.

Why this exists
---------------
README parsers see a tech keyword in prose and add it to the detected
tech list. But the keyword may appear in a NEGATIVE context:

    "This is not a Python application."
    "We don't use Flask."
    "Instead of React, we built our own renderer."

In every case the README is disclaiming the tech, not declaring it.
Treating these as evidence pollutes downstream skill matching with
techs the project does not use.

Behaviour
---------
``keyword_has_non_negated_mention(keyword, content_lower)`` returns
True iff ``keyword`` appears in ``content_lower`` at least once
OUTSIDE a negation window. The window is small (``~40 chars``, roughly
6-8 words) so it scopes to one sentence-segment in normal prose.

A tech is dropped only if EVERY one of its matches is negated. A
single non-negated mention is enough to keep the tech.

The helper expects ``content_lower`` to already be lowercased; the
caller is responsible. The negation regex itself is also lowercase,
so both sides match in lower-case space.
"""

from __future__ import annotations

import re

# Negation tokens that, when they appear shortly BEFORE a tech keyword,
# indicate the surrounding text is disclaiming rather than declaring it.
NEGATION_RE = re.compile(
    r"\b(?:"
    r"not(?:\s+(?:a|an|the))?|"
    r"isn'?t|aren'?t|wasn'?t|weren'?t|"
    r"doesn'?t|don'?t|didn'?t|"
    r"no\s+longer|instead\s+of|rather\s+than|"
    r"without|never|nor"
    r")\b"
)

# Window size (characters) in which a negation token is considered to
# scope over a following keyword. ~6-8 words; one sentence-segment.
NEGATION_PROXIMITY_CHARS = 40


def keyword_has_non_negated_mention(
    keyword: str,
    content_lower: str,
    *,
    word_boundary: bool = True,
) -> bool:
    """Return True iff ``keyword`` appears in ``content_lower`` at least
    once OUTSIDE a negation context.

    Parameters
    ----------
    keyword : the tech name to search for (e.g. ``"python"``,
        ``"fast api"``). Must already be lowercase.
    content_lower : the text to search in. Must already be lowercase
        (the caller does this once; the function does not re-lower).
    word_boundary : when True (default), the keyword is matched with
        ``\\b`` word boundaries to avoid partial-substring false
        positives (``"jython"`` won't match ``"python"``). When False,
        substring matching is used — useful for short multi-word
        keywords that callers want to match permissively.

    Returns
    -------
    bool — True if at least one non-negated match exists; False if the
    keyword is absent, or if every match falls inside a negation window.
    """
    if word_boundary:
        pattern = re.compile(rf"\b{re.escape(keyword)}\b")
    else:
        pattern = re.compile(re.escape(keyword))
    matches = list(pattern.finditer(content_lower))
    if not matches:
        return False
    for m in matches:
        window_start = max(0, m.start() - NEGATION_PROXIMITY_CHARS)
        window = content_lower[window_start : m.start()]
        if not NEGATION_RE.search(window):
            return True
    return False
