# Cogs
A cog is a collection of commands, listeners, and optional states to help group commands together.

> **Cogs can only be one file; never split logical groups across multiple files**

## Skills
- See `.agents/skills/cogs` for cog structure, decorators, and task lifecycle guidance.
- See `.agents/skills/error-handling` for error handling and logging guidance.

## Cog List
- admin.py
- easter.py
- guild.py
- internal.py
- moderation.py
- profile.py
- radio.py
- twitch.py
- twitter.py
- utility.py
- welcome.py
- xp.py
- youtube.py

## radio.py
> **Watch for race conditions; always default to useing wavelink's built-in functions instead of desinging your own.**

- Requires Lavalink to be running (`docker compose up -d lavalink`) before the cog can connect or play audio.
- `Wavelink v3.5` is the API package for Lavalink.
- Volume must always be between 0 and 100.
- Common functions should be reused as much as possible.