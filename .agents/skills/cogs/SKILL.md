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

## Commands and Listeners
- Every prefix command is marked with the `@commands.command()` decorator.
- Every slash command is marked with the `@app_commands.command()` decorator.
- Every hybrid command (accessible using both prefix and slash methods) is marked with the `@commands.hybrid_command()` decorator.
- Every listener is marked with the `@commands.Cog.listener()` decorator.

## UI Classes
UI classes (`discord.ui.ChannelSelect`, `discord.ui.LayoutView`, etc.) always live in the same file as the cog that uses them; never extract to a separate file.

## Loading and Unloading Behaviors
To define loading and unloading behaviors:
```python
async def cog_load(self) -> None:
    """Custom Load Behavior"""
    ...

async def cog_unload(self) -> None:
    """Custom Unload Behavior"""
    ...
```

## Tasks
- Functions that need to be run at specified intervals use the `@tasks.loop()` decorator.
- Tasks must be explicitly started and stopped in cog loading and unloading
```python
async def cog_load(self) -> None:
    self.my_task.start()

async def cog_unload(self) -> None:
    self.my_task.stop()
```

## Scoping
Cogs and/or commands must be scoped using specific decorators:
- **`@app_commands.guild_only()`:** commands can only be used in guilds.
- **`@app_commands.dm_only()` or `@commands.dm_only()`:** commands can only be used in DMs.
- **`@app_commands.checks.has_role("CENBot Admin")` or `@commands.has_role("CENBot Admin")`:** commands can only be used by users with the "CENBot Admin" role.
- **`@app_commands.checks.is_owner()` or `@commands.is_owner()`:** commands can only be used by the bot owner.

## Structure
Every cog file follows this structure:
1. Module docstring + dunder block (see `conventions` skill)
2. Imports (see `conventions` skill)
3. UI classes (if any)
4. Cog class
5. `setup()` function

**Setup Function**:
```python
async def setup(bot: CENBot) -> None:
    await bot.add_cog(MyCog(bot))
```
