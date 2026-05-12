---
name: conventions-python
description: Use when writing, reviewing, or refactoring python files in CEN-Bot that need repo-specific conventions for imports, module metadata, inline comments, and code style.
---

# Conventions
> **Always re-read a file immediately before writing to it**

## Dunder Block
Every file gets a module-level docstring followed by a dunder block:
```python
"""Short description of what this module does."""

__author__ = ["Author Name"]      # person(s) who created the file
__copyright__ = "Copyright CEN"   # always this value
__credits__ = ["Name", "Name"]    # all contributors, including Claude
__version__ = "1.0.0"             # major.minor.bug
__status__ = "Development"        # "Development" → "Production"
```

## Import Order
All files follow this group order and each group separated by a blank line and labeled with a comment:
```python
# Standard library
import os
from logging import getLogger

# Third-party
import discord
from discord.ext import commands

# Internal
from start import CENBot
```
> **Only include groups that are needed; omit empty ones**

## Inline Comments
- Groups of functions must be commented with `### Label ###` before the group.
- Every logical block within a function must have a comment describing what it does.
- Avoid restating what the code says; omit comments that are redundant with the code itself.
- Use `# TODO:` for planned work and `# FIXME:` for known issues.

## Versioning
- All files use semantic versioning: `MAJOR.MINOR.PATCH`.
  - `Major`: Increments for breaking changes that are not backward-compatible. 
  - `Minor`: Increments for new, backward-compatible functionality.
  - `Patch`: Increments for backward-compatible bug fixes.
- All files should denote their status: `developmental` or `production`.
  - `0.x.x` versioning indicates a developmental version where large changes are expected.