---
name: cogs
description: Use when creating or modifying files in `cogs/` that need CEN-Bot-specific structure, Discord command patterns, task lifecycle handling, and cog organization rules.
---

# Cogs
A cog is a collection of commands, listeners, and optional states to help group commands together.

> **Cogs can only be one file; never split logical groups across multiple files**

## `Cog` vs `GroupCog`
- `commands.Cog`: use for cogs with unrelated or standalone commands
- `commands.GroupCog`: use for cogs where all commands belong to the same slash command group
  - Must call `super().__init__()` after setting instance variables

## Scoping
Cogs and/or commands must be scoped using specific decorators:
- **`@app_commands.guild_only()`:** commands can only be used in guilds.
- **`@app_commands.dm_only()` or `@commands.dm_only()`:** commands can only be used in DMs.
- **`@app_commands.checks.has_role("CENBot Admin")` or `@commands.has_role("CENBot Admin")`:** commands can only be used by users with the "CENBot Admin" role.
- **`@app_commands.checks.is_owner()` or `@commands.is_owner()`:** commands can only be used by the bot owner.

## Cog Structure
Every cog file follows this structure:
1. Module docstring + dunder block (see `conventions-python` skill)
2. Imports (see `conventions-python` skill)
3. Optional: external helper functions, @dataclass definitions, etc.
4. Optional: UI classes (if any)
5. Cog class
    1. `__init__()` function
    2. Optional: `cog_load()` and `cog_unload()` functions
    3. Optional: internal helper functions
    4. Commands
    5. Listeners
    6. Optional: tasks
6. `setup()` function

**Setup Function**:
```python
async def setup(bot: CENBot) -> None:
    await bot.add_cog(MyCog(bot))
```

### UI Classes
UI classes (`discord.ui.ChannelSelect`, `discord.ui.LayoutView`, etc.) always live in the same file as the cog using them; never extract to a separate file.

### `cog_load()` and `cog_unload()`
Optional methods defining custom behavior when the cog is loaded and unloaded.
```python
async def cog_load(self) -> None:
    """Custom Load Behavior"""
    ...

async def cog_unload(self) -> None:
    """Custom Unload Behavior"""
    ...
```
**Note:** `cog_unload()` is not guaranteed to be called in all cases (e.g. if the bot crashes); it should not be relied on for critical cleanup tasks.

### Commands and Listeners
- Every prefix command is marked with the `@commands.command()` decorator.
- Every slash command is marked with the `@app_commands.command()` decorator.
- Every hybrid command (accessible using both prefix and slash methods) is marked with the `@commands.hybrid_command()` decorator.
- Every listener is marked with the `@commands.Cog.listener()` decorator.

### Tasks
- Functions that need to be run at specified intervals use the `@tasks.loop()` decorator.
- Tasks must be explicitly started and stopped in cog loading and unloading
```python
async def cog_load(self) -> None:
    self.my_task.start()

async def cog_unload(self) -> None:
    self.my_task.stop()
```

## Database Queries
- Always use explicit column lists in `SELECT`; never use `SELECT *`
- Correlated subqueries (e.g. `COUNT(*)`) are acceptable for counting related data in single-round-trip fetches.