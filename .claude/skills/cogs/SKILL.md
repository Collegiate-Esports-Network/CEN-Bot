---
name: cogs
description: Cog structure and conventions for CEN-Bot. Use this skill whenever creating or modifying any cog file in `cogs/`.
---

# Cogs

## `Cog` vs `GroupCog`
- `commands.Cog`: use for cogs with unrelated or standalone commands
- `commands.GroupCog`: use for cogs where all commands belong to the same slash command group
  - Must call `super().__init__()` after setting instance variables

## Structure
> **All commands that belong together live in one file as one `GroupCog`; never split a logical group across multiple files**

Every cog file follows this structure:
1. Module docstring + dunder block (see `conventions` skill)
2. Imports (see `conventions` skill)
3. UI classes (if any)
4. Cog class
5. `setup()` function

```python
async def setup(bot: CENBot) -> None:
    await bot.add_cog(MyCog(bot))
```

## `@app_commands.command` vs `@commands.command`
- `@app_commands.command`: use for slash commands
- `@commands.command`: use for prefix (non-slash) commands

## Decorators
- All guild-facing cogs must be decorated with `@app_commands.guild_only()` or `@commands.guild_only()`
- All DM-only cogs must be decorated with `@app_commands.dm_only()` or `@commands.dm_only()`
- Admin commands must be decorated with `@app_commands.checks.has_role("CENBot Admin")` or `@commands.has_role("CENBot Admin")`
- Owner-only commands must be decorated with `@app_commands.checks.is_owner()` or `@commands.is_owner()`

## Cog Loading
To define loading and unloading behaviors:
```python
async def cog_load(self) -> None:
    """Custom Load Behavior"""
    self.custom_load_behavior()

async def cog_unload(self) -> None:
    """Custom Unload Behavior"""
    self.custom_unload_behavior()
```

## Task Loops
Start and stop task loops in `cog_load`/`cog_unload`:
```python
async def cog_load(self) -> None:
    """Start the polling task loop."""
    self.check_task.start()

async def cog_unload(self) -> None:
    """Stop the polling task loop."""
    self.check_task.stop()
```

## UI Classes
UI classes (`discord.ui.ChannelSelect`, `discord.ui.LayoutView`, etc.) always live in the same file as the cog that uses them; never extract to a separate file.