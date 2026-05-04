"""Main file of the CEN Discord client"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

# Standard library
import argparse
import logging
import logging.config
import os

import asyncpg
import discord
# Third-party
import yaml
from asyncpg.exceptions import PostgresError
from discord.ext.commands import Bot, ExtensionError, ExtensionNotFound
from dotenv import load_dotenv

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
        self.version = "1.1.0"

    async def setup_hook(self) -> None:
        """Create the DB connection pool, load all cogs, and sync slash commands.

        Runs once before the bot connects to the gateway. Exits with code 1 if
        the database connection cannot be established.
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