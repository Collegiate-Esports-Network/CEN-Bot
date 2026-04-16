# CEN-Bot
Custom Discord bot for the Collegiate Esports Network

## Project Structure
```
cogs/               - modules loaded at runtime
logging.yaml        - logging configuration
start.py            - entry point for custom bot
.env.dev            - development environment variables
.env.prod           - production environment variables
.env.local          - shared environment variables

```

## Architecture
- Python: `v3.14`
- Discord API library: `discord.py[voice]`
- Database driver: `asyncpg`
  - async PostgreSQL, parameterized queries use `$1`, `$2`, etc.
  
## Development
> **Always re-read a file immediately before writing to it**

**Run the bot:**
```bash
python start.py --env dev   # development environment
python start.py --env prod  # production environment
```

**Build Docs:**
```bash
sphinx-build -b html docs docs/_build/html
```

### Conventions
- Every cog has a matching logger: `log = getLogger('CENBot.<cog_name>')`
  - New cogs must be added to `logging.yaml`
- Slash commands take `discord.Interaction` as the first parameter
  - User-only responses must have `ephemeral=True`
  - Public responses must have `ephemeral=False`
- Prefix commands use `commands.Context` as the first parameter
- Admin commands require the invoker to have the `"CENBot Admin"` role

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