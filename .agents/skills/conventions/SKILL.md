---
name: conventions
description: Use when writing, reviewing, or refactoring Python files in CEN-Bot that need repo-specific conventions for imports, module metadata, inline comments, and SQL query style.
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
- Comment every logical block with a short label.
- Avoid restating what the code says.
- Use `# TODO:` for planned work and `# FIXME:` for known issues.

## Database Queries
- Always use explicit column lists in `SELECT`; never use `SELECT *`
- Correlated subqueries (e.g. `COUNT(*)`) are acceptable for counting related data in single-round-trip fetches.
