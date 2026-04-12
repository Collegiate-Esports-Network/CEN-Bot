---
name: conventions
description: Code style, import order, and documentation conventions for CEN-Bot. Use this skill whenever writing, reviewing, or modifying any Python file in CEN-Bot.
---

# Conventions

## Import Order
> **Only include groups that are needed; omit empty ones**

All files follow this group order, each group separated by a blank line and labeled with a comment:
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

## Inline Comments
- Comment every logical block with a short label
- Avoid restating what the code says
- Use `# TODO:` for planned work and `# FIXME:` for known issues