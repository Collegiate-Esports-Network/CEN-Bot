# CEN-Bot
This repo contains all files necessary to run the Collegiate Esports Network's custom Discord bot.

## File Structure
```
cogs/               - modules loaded at runtime
lavalink/           - lavalink server config and plugins
utils/              - helper functions
logging.yaml        - logging configuration
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
> **Always re-read a file immediately before writing to it**
- See `.agents/skills/conventions` for shared Python and SQL conventions.
- See `.agents/skills/docstrings` for Sphinx docstring requirements.

## Containers
- `compose.yaml`: base config (no env files); always used.
- `compose.override.yaml`: dev env files + source bind mount; merged automatically when no `-f` flag is given.
- `compose.prod.yaml`: prod env files; must be merged explicitly with `-f`.

**Dev** (auto-merges override):
```bash
docker compose up -d [lavalink] [bot]    # start (omit service names to start all)
docker compose stop [lavalink] [bot]     # stop
```

**Prod**:
```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d [lavalink] [bot]
docker compose stop [lavalink] [bot]
```

## Database
> **Never connect to, modify, query, or run migrations against the remote/production Supabase instance**

**Database Control:**
```bash
# From `../Database/`
npx supabase start   # start local instance
npx supabase stop    # stop local instance
npx supabase status  # status of the instance
```
- **Local API:** `http://localhost:54321`
- **MCP:** Available via `supabase_local` MCP

### Migrations/Changes
```bash
# From `../Database`
npx supabase migration new <description>   # create a new migration file
npx supabase migration up                  # apply pending migrations to local DB
```