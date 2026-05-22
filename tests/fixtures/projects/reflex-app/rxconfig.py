"""Reflex configuration file — the hallmark signal that this is a Reflex project.

A Reflex app developer writes pure Python; Reflex transpiles to React in the
``.web/`` directory at build time. Bug8 in ListOfBugs/: PRG scanned ``.web/``
during tech detection and concluded this was a ``react-app`` with
``[react, node, nextjs, typescript]`` in the tech_stack. The fixture
reproduces that exact shape.
"""

import reflex as rx

config = rx.Config(
    app_name="my_app",
    plugins=[],
)
