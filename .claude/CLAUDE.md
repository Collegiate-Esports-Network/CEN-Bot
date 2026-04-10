# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Bot

```bash
python start.py --env dev    # development environment
python start.py --env prod   # production environment
```

The `--env` flag is required. It loads `.env.local` first (shared keys like `YOUTUBE_KEY`), then the environment-specific file (`.env.dev` or `.env.prod`) which must contain `TOKEN` and `SUPABASE_CONN_STRING`.

The bot is also containerized:
```bash
docker build -t cen-bot .
docker run -e NODE_ENV=prod cen-bot
```

## Linting

```bash
pyflakes .          # import/undefined name checks
pycodestyle .       # PEP 8 style checks
```

Note: the linter runs automatically on file save in VSCode and modifies files. Always re-read a file immediately before writing it to avoid stale-state write errors.

## Architecture

**Entry point**: `start.py` — defines `CENBot(Bot)`, creates an `asyncpg` connection pool at `bot.db_pool`, auto-loads all `cogs/*.py` via `load_extension`, and force-syncs the slash command tree on startup.

**Cogs** (`cogs/`): Each file is a `commands.Cog` or `commands.GroupCog` loaded by `start.py`. All guild-facing cogs are decorated with `@app_commands.guild_only()`. GroupCog subclasses must call `super().__init__()` after `self.bot = bot`.

- `admin.py` — Prefix commands (`!!sync`, `!!load`, `!!reload`, `!!unload`, `!!announce`) restricted to DM + bot owner. Uses `ForAsync` to iterate guild list for announce.
- `moderation.py` — Guild moderation: configurable logging channel, report channel, moderation level. Context menus for reporting messages/users. Listeners for `on_message_edit`, `on_message_delete`, `on_voice_state_update`.
- `guilds.py` — Guild setup commands and per-module enable/disable status display.
- `welcome.py` — Welcome message configuration and `on_member_join` listener.
- `youtube.py` — YouTube upload alerts: polls every 10 minutes via `check_youtube` task loop. Guilds subscribe to channels; alerts fire to `youtube_alert_channel`.
- `utility.py` — `/ping`, `/about`, `/flip`, `/utc`, `/weather` slash commands. `update_presence` task loop rotates bot status with weather every minute.
- `easter.py` — Hidden easter egg listener and `!!rickroll` prefix command.
- `internal.py` — `on_guild_join` (insert to DB), `on_guild_remove` (delete from DB), `on_thread_create` (auto-join thread).
- `rewrites/xp.py` — XP system: `on_message` awards 1–3 XP probabilistically; `/xp xp` and `/xp leaderboard` slash commands.

**Modules** (`modules/`):
- `async_for.py` — `ForAsync`: wraps a plain list as an async iterator for use in `async for` loops.
- `app_errors.py` / `commands_errors.py` — Custom `CheckFailure` subclasses for app commands and prefix commands respectively.

## Database

PostgreSQL via **asyncpg** (direct TCP, ~1ms) using Supabase as host. Connection string from `SUPABASE_CONN_STRING` env var. SSL is required; the cert is `prod-ca-2021.crt` in the repo root.

Schema is `cenbot`. Key tables:
- `cenbot.guilds` — per-guild config: `guild_id`, `youtube_alert_channel`, module enable flags
- `cenbot.youtube` — YouTube subscriptions: `channel_id`, `upload_playlist_id`, `subscribed_guilds` (array), `last_upload_date`
- `cenbot.moderation` — per-guild moderation config
- `cenbot.welcome` — per-guild welcome message config
- `xp` (no schema prefix) — `user_id`, per-guild XP columns named `s_{guild_id}`

All DB calls use `async with self.bot.db_pool.acquire() as conn:` and parameterized queries (`$1`, `$2`, ...).

## Code Conventions

- Module-level docstring at top, then `__author__`/`__version__`/etc. dunder block.
- Imports grouped: Standard library → Third-party → Internal, each with a comment.
- Logger per-cog: `log = getLogger('CENBot.<cogname>')`.
- Class names: CamelCase (`CENBot`, `Admin`, `Moderation`, etc.).
- All slash commands use `discord.Interaction` as first parameter; prefix commands use `commands.Context`.
- `ephemeral=True` for user-only responses; `ephemeral=False` (or omitted) for public responses.
- Required Discord role for admin commands: `"CENBot Admin"`.
- Class and functions use the sphix docstyle.