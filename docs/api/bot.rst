Bot (start.py)
==============

The entry point. Defines :class:`~start.CENBot`, wires up the ``asyncpg``
connection pool, auto-loads every ``cogs/*.py`` extension, and force-syncs
the slash command tree on startup.

.. automodule:: start
   :members:
   :show-inheritance:
   :special-members: __init__
