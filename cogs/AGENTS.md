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
- radio.py
- twitch.py
- utility.py
- welcome.py
- xp.py
- youtube.py

## radio.py
Requires Lavalink to be running (`docker compose up -d`) before the cog can connect or play audio. Wavelink will raise on connect if the node is unreachable.