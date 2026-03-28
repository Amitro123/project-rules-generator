"""Single source of truth for the CLI version."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("project-rules-generator")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.2.2"
