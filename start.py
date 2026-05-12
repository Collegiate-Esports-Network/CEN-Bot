"""Main file of the CEN Discord client"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = ["Justin Panchula", "Claude"]
__version__ = "1.1.0"
__status__ = "Production"

# Standard library
import argparse
import logging
import logging.config
import os

# Third-party
import asyncpg
import discord
import yaml
from asyncpg.exceptions import PostgresError
from discord.ext.commands import Bot, ExtensionError, ExtensionNotFound
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient

# Internal
from utils.realtime import RealtimeManager

# Ensure log directory exists before loading config
os.makedirs('logs', exist_ok=True)

# Configure logging
with open('logging.yml', 'r') as f:
    logging.config.dictConfig(yaml.safe_load(f.read()))
log = logging.getLogger('CENBot')

# Init intents
intents = discord.Intents.all()


class CENBot(Bot):
    """The main bot class for CEN.

    Extends :class:`discord.ext.commands.Bot` with a Supabase connection pool
    and automatic cog loading from the ``cogs/`` directory.
    """

    def __init__(self) -> None:
        """Initialise the bot with all intents and the ``!!`` command prefix."""
        super().__init__(
            intents=intents,
            description="Hello! I'm the CEN Bot, a customized bot built and maintained by Collegiate Esports Network LLC.",
            command_prefix="!!"
        )
        self.version = __version__
        self.supabase: AsyncClient | None = None
        self.realtime: RealtimeManager | None = None

    async def setup_hook(self) -> None:
        """Create the DB connection pool, load all cogs, and sync slash commands.

        Runs once before the bot connects to the gateway. Exits with code 1 if
        the database connection cannot be established. The Supabase realtime
        client is initialised best-effort: failure logs but does not abort
        startup, since most cogs do not depend on it.
        """
        log.info("Connecting...")

        # Create DB connection
        try:
            self.db_pool: asyncpg.Pool = await asyncpg.create_pool(
                dsn=os.getenv('SUPABASE_CONN_STRING'),
                ssl='prefer',
                statement_cache_size=0
            )
        except OSError as e:
            log.exception(e)
            exit(1)
        except PostgresError as e:
            log.exception(e)
            exit(1)
        else:
            log.info("Supabase connection established")

        # Initialise the async Supabase client + realtime manager (used by profile cog)
        self.web_base_url: str = os.getenv('WEB_BASE_URL', 'https://collegiateesportsnetwork.org').rstrip('/')
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SECRET_KEY')
        if supabase_url and supabase_key:
            try:
                self.supabase = await acreate_client(supabase_url, supabase_key)
                self.realtime = RealtimeManager(self.supabase)
            except Exception as e:
                log.exception(e)
                log.warning("Supabase realtime client unavailable; profile cog will degrade")
        else:
            log.warning("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set; realtime disabled")

        # Load extensions from cogs folder
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                try:
                    await self.load_extension(f"cogs.{file[:-3]}")
                except ExtensionNotFound:
                    log.warning(f"cog '{file[:-3]}' not found")
                except ExtensionError as e:
                    log.warning(f"cog '{file[:-3]}' not loaded properly: {e}")
                else:
                    log.info(f"cog '{file[:-3]}' loaded successfully")

        # Force command sync
        await self.tree.sync()

    async def close(self) -> None:
        """Tear down realtime watchers and the DB pool before closing the gateway."""
        # Stop active realtime channels first; they hold open websockets
        if self.realtime is not None:
            try:
                await self.realtime.close()
            except Exception as e:
                log.exception(e)

        await super().close()

    async def on_ready(self) -> None:
        """Log a confirmation message once the bot has connected and is ready."""
        log.info(f"{self.user.display_name} has logged in")


def start(args: argparse.Namespace):
    """Load environment variables and run the bot.

    Loads ``.env.local`` first (shared API keys), then the environment-specific
    file (``.env.development`` or ``.env.production``) selected by ``args.env``. Exits with
    code 1 if the environment is invalid or the bot token is missing.

    :param args: parsed CLI arguments; expects ``args.env`` to be ``'dev'`` or ``'prod'``
    :type args: argparse.Namespace
    """
    log.info("Loading local environment variables...")
    load_dotenv('.env.local')

    if args.env == "prod":
        log.info("Loading production environment variables...")
        load_dotenv('.env.production')
    elif args.env == "dev":
        log.info("Loading development environment variables...")
        load_dotenv('.env.development')
    else:
        log.error("Invalid environment specified, exiting...")
        exit(1)

    token = os.getenv('TOKEN')
    if token:
        log.info("Token found, starting bot...")
        bot = CENBot()
        bot.run(token=token, log_handler=None)
    else:
        log.error("Token not found, exiting...")
        exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', dest='env', type=str, help="Must be one of `['dev', 'prod']`")
    start(parser.parse_args())