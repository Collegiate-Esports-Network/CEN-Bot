# CEN-Bot
This repo contains all files necessary to run the Collegiate Esports Network's custom Discord bot.

## File Structure
```
cogs/               - modules loaded at runtime
lavalink/           - lavalink server config and plugins
utils/              - helper functions
logging.yml         - logging configuration
start.py            - entry point for custom bot
.env.dev            - development environment variables
.env.prod           - production environment variables
.env.local          - shared environment variables
```

## Architecture
- Language: `Python v3.14`
- Discord API library: `discord.py[voice]`
  - `[voice]` includes extra packages required for interacting with voice channels.
- Database: `Supabase`
  - Driver: `asyncpg`; Paramaterize queries using `$1`, `$2`, etc.
- Audio server: `Lavalink v4`
  - Middleware: `Wavelink v3`

## Conventions
> **Always re-read a file immediately before writing to it.**

- See `.agents/skills/conventions-python` for Python file requirements.
- See `.agents/skills/docstrings` for Sphinx docstring requirements.

## Containers
- `compose.yml`: base config (no env files); always used.
- `compose.override.yml`: dev env files + source bind mount; merged automatically when no `-f` flag is given.
- `compose.prod.yml`: prod env files; must be merged explicitly with `-f`.

**Dev:** (auto-merges override)
```bash
docker compose up -d [lavalink] [bot]    # Start (omit service names to start all)
docker compose stop [lavalink] [bot]     # Stop
```

**Prod:**
```bash
docker compose -f compose.yml -f compose.prod.yml up -d [lavalink] [bot]
docker compose stop [lavalink] [bot]
```

## Database
> **Never connect to, modify, query, or run migrations against the remote/production Supabase instance.**

**Database Control:**
```bash
# From `../Database/`
npx supabase start   # Start local instance
npx supabase stop    # Stop local instance
npx supabase status  # Status of the instance
```
- **Local API:** `http://localhost:54321`
- **MCP:** Available via `supabase_local` MCP

### Migrations/Changes
```bash
# From `../Database`
npx supabase migration new <description>   # Create a new migration file
npx supabase migration up                  # Apply pending migrations to local DB
```