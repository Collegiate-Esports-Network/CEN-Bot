---
name: docstrings
description: Sphinx docstring conventions for CEN-Bot. Use this skill whenever writing or reviewing docstrings on any class, method, or function in CEN-Bot.
---

# Docstrings

## Standard Format
All classes, methods, and functions require a Sphinx-style docstring:

```python
def example(self, interaction: discord.Interaction, value: int) -> None:
    """Short imperative description.

    Optional longer explanation for non-obvious behaviour.

    :param interaction: the discord interaction
    :type interaction: discord.Interaction
    :param value: description of the parameter
    :type value: int
    :returns: description (omit if None)
    :rtype: type (omit if None)
    """
```

## Per-Context Rules

### Classes
Describes what the class represents or does:
```python
class TwitchAlertChannelSelect(discord.ui.ChannelSelect):
    """Saves the chosen text channel as the guild's Twitch live alert channel."""
```

### `__init__`
Document non-trivial initialisers; skip if it only sets `self.bot`:
```python
def __init__(self, bot: CENBot, current_channel_id: int | None) -> None:
    """Initialise with the currently configured alert channel pre-selected.

    :param bot: the bot instance
    :type bot: CENBot
    :param current_channel_id: the ID of the currently set channel, or ``None``
    :type current_channel_id: int | None
    """
```

### `cog_load` / `cog_unload`
One-liner only; describe what is started or stopped:
```python
def cog_load(self) -> None:
    """Start the Twitch polling task loop."""

def cog_unload(self) -> None:
    """Stop the Twitch polling task loop."""
```

### Task Loops
Must describe poll interval, what is checked, and firing conditions:
```python
@tasks.loop(minutes=3)
async def check_twitch(self) -> None:
    """Poll subscribed Twitch channels for live status changes.

    Runs every 3 minutes. Batches up to 100 channel IDs per ``/helix/streams``
    call. Fires an alert only on a ``is_live`` false → true transition to avoid
    repeated notifications while a stream is ongoing.
    """
```

### UI Callbacks
Always document; note what is persisted and what feedback is given:
```python
async def callback(self, interaction: discord.Interaction) -> None:
    """Persist the selected alert channel and confirm to the user.

    :param interaction: the discord interaction triggered by the select
    :type interaction: discord.Interaction
    """
```