# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Bot

```bash
python start.py --env dev    # development environment
python start.py --env prod   # production environment
```

The `--env` flag is required. It loads `.env.local` first (shared keys like `YOUTUBE_KEY`, `TWITCH_CLIENT`, `TWITCH_SECRET`), then the environment-specific file (`.env.dev` or `.env.prod`) which must contain `TOKEN` and `SUPABASE_CONN_STRING`.

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

- `admin.py` — Prefix commands (`!!sync`, `!!load`, `!!reload`, `!!unload`, `!!announce`) restricted to DM + bot owner. `announce` accepts an optional `delay_minutes` arg and fires as a background task.
- `internal.py` — Global error handlers: wires `bot.tree.on_error` for app commands, `on_command_error` for prefix commands, `on_error` for raw event exceptions; DMs the bot owner on unhandled errors. Also handles `on_guild_join`/`on_guild_remove` (DB sync) and `on_thread_create` (auto-join).
- `moderation.py` — Guild activity logging with 5 verbosity levels (0–4). Config (level, log channel, report channel, new-member timeout) loaded into memory on `cog_load` — zero DB queries during events. Context menus for reporting messages/users. Commands: `configure` (View UI), `timeout`, `status`.
- `guilds.py` — Guild setup commands and per-module enable/disable status display.
- `welcome.py` — Welcome message configuration and `on_member_join` listener.
- `youtube.py` — YouTube upload alerts: polls every 10 minutes via `check_youtube` task loop. Guilds subscribe to channels; alerts fire to `youtube_alert_channel`.
- `twitch.py` — Twitch live alerts: polls every 3 minutes via `check_twitch` task loop. Uses Twitch Helix API with Client Credentials OAuth2 (token cached in memory). Guilds subscribe to streamers; alerts fire to `twitch_alert_channel`. Batches up to 100 channel IDs per `/helix/streams` call. Fires only on `is_live` false → true transition.
- `utility.py` — `/ping`, `/about`, `/help`, `/flip`, `/utc`, `/weather` slash commands. `update_presence` task loop rotates bot status with weather every minute.
- `easter.py` — Hidden easter egg listener and `!!rickroll` prefix command.
- `xp.py` — XP system: `on_message` awards 1–3 XP probabilistically; `/xp xp` and `/xp leaderboard` slash commands.

## Database

PostgreSQL via **asyncpg** (direct TCP) using Supabase as host. Connection string from `SUPABASE_CONN_STRING` env var. SSL is required; the cert is `prod-ca-2021.crt` in the repo root. Use the **Transaction mode pooler** (port 6543) — Session mode hits client limits with asyncpg's own pool. The direct connection (port 5432) is IPv6-only and will fail on IPv4-only machines.

Schema is `cenbot`. Key tables:
- `cenbot.guilds` — per-guild config: `id`, `youtube_alert_channel`, `twitch_alert_channel`, module enable flags
- `cenbot.youtube` — YouTube subscriptions: `channel_id`, `upload_playlist_id`, `subscribed_guilds` (array), `last_upload_date`
- `cenbot.twitch` — Twitch subscriptions: `user_id`, `login`, `display_name`, `subscribed_guilds` (array), `is_live`
- `cenbot.moderation` — per-guild moderation config
- `cenbot.welcome` — per-guild welcome message config
- `xp` (no schema prefix) — `user_id`, per-guild XP columns named `s_{guild_id}`

All DB calls use `async with self.bot.db_pool.acquire() as conn:` and parameterized queries (`$1`, `$2`, ...).

## Code Conventions

- Module-level docstring at top, then `__author__`/`__version__`/etc. dunder block.
- Imports grouped: Standard library → Third-party → Internal, each with a comment.
- Logger per-cog: `log = getLogger('CENBot.<cogname>')`. New cogs must also be added to `logging.yaml`.
- Class names: CamelCase (`CENBot`, `Admin`, `Moderation`, etc.).
- All slash commands use `discord.Interaction` as first parameter; prefix commands use `commands.Context`.
- `ephemeral=True` for user-only responses; `ephemeral=False` (or omitted) for public responses.
- Required Discord role for admin commands: `"CENBot Admin"`.

### Docstrings and Comments

Every class, method, and function must have a docstring. Follow the Sphinx style throughout:

```python
def example(self, interaction: discord.Interaction, value: int) -> None:
    """Short imperative summary of what this does.

    Longer explanation if the behaviour is non-obvious (optional).

    :param interaction: the discord interaction
    :type interaction: discord.Interaction
    :param value: description of the parameter
    :type value: int
    """
```

Specific rules:
- **Classes** — docstring describes what the class *represents* or *does*. For dataclasses, document fields with `:param name:` / `:type name:` in the class docstring rather than on `__init__`.
- **`__init__`** — document non-trivial initialisers (those that set more than just `self.bot`). Skip the docstring only for truly trivial one-liners.
- **`cog_load` / `cog_unload`** — always add a one-line docstring describing what is started/registered or stopped/removed.
- **Task loops** — docstring must describe the poll interval, what is checked, and any firing conditions (e.g. state transitions).
- **UI callbacks** (`callback`, `on_submit`, `on_error`) — always docstring; note what is persisted and what feedback is given.
- **Inline comments** — use sparingly for logic that is not self-evident. Avoid restating what the code already says.
