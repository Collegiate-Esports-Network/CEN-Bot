# CEN-Bot
This repo contains all files necessary to run the Collegiate Esports Network's custom Discord bot.

## Project Structure
```
cogs/               - modules loaded at runtime
utils/              - helper functions
logging.yaml        - logging configuration
start.py            - entry point for custom bot
.env.dev            - development environment variables
.env.prod           - production environment variables
.env.local          - shared environment variables
```

## Architecture
- Python: `v3.14`
- Discord API library: `discord.py[voice]`
  - `[voice]` includes extra packages required for interacting with voice channels.
- Database driver: `asyncpg`
  - Parameterized queries use `$1`, `$2`, etc.
  
## Conventions
> **Always re-read a file immediately before writing to it**
- See `.agents/skills/conventions` for shared Python and SQL conventions.
- See `.agents/skills/docstrings` for Sphinx docstring requirements.

## Starting the Bot
```bash
python start.py --env dev   # development environment
python start.py --env prod  # production environment
```

## Build Docs
```bash
sphinx-build -b html docs docs/_build/html
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
