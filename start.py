__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Main file of the CEN Discord client"""

# Python imports
import argparse

# Discord imports
import discord
from discord.ext.commands import Bot
from discord.ext.commands import ExtensionError, ExtensionNotFound

# Python imports
from dotenv import load_dotenv
import os
import ssl

# Logging imports
import logging
import logging.config
import yaml

# Database imports
import asyncpg
from asyncpg.exceptions import PostgresError

# Configure logging
logging.config.dictConfig(yaml.safe_load(open('logging.yaml', 'r').read()))
log = logging.getLogger('CENBot')


# Init intents
intents = discord.Intents.all()


# Create a custom bot class
class cenbot(Bot):
    def __init__(self) -> None:
        super().__init__(
            intents=intents,
            description="Hello! I'm the CEN Bot, a customized bot built and maintained by Collegiate Esports Network LLC.",
            command_prefix="!!"
        )
        self.version = "1.0.1"

    async def setup_hook(self) -> None:
        log.info(f"{self.user.display_name} is connecting...")

        # Create DB connection
        try:
            self.db_pool: asyncpg.Pool = await asyncpg.create_pool(
                dsn=os.getenv('SUPABASE_CONN_STRING'),
                ssl=ssl.SSLContext(ssl.PROTOCOL_SSLv23).load_verify_locations(
                    capath=os.path.join(os.path.dirname(__file__), 'prod-ca-2021.crt')),
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
                    log.info(f"cog '{file[:-3]}' loaded succesfully")

        # Force command sync
        await self.tree.sync()

    # async def on_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
    #     # Get owner
    #     owner = self.get_user(self.owner_id)
    #     if owner is None:
    #         try:
    #             owner = await self.fetch_user(self.owner_id)
    #         except discord.HTTPException:
    #             owner = None

    #     if owner:
    #         try:
    #             await owner.send("Error")
    #         except discord.Forbidden:
    #             log.warning("DMs unavailable.")

    async def on_ready(self) -> None:
        log.info(f"{self.user.display_name} has logged in")


def start(args: argparse.Namespace):
    # Load local environment variables
    log.info("Loading local environment variables...")
    load_dotenv('.env.local')

    if args.env == "prod":
        log.info("Loading production environment variables...")
        load_dotenv('.env.prod')
    elif args.env == "dev":
        log.info("Loading development environment variables...")
        load_dotenv('.env.dev')
    else:
        log.error("Invalid evironment specificed, exiting...")
        exit(1)

    # Get token from environment variables
    token = os.getenv('TOKEN')
    if token:
        log.info("Token found, starting bot...")
        bot = cenbot()
        bot.run(token=token, log_handler=None)
    else:
        log.error("Token not found, exiting...")
        exit(1)


# Start the bot
if __name__ == '__main__':
    # Argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', dest='env', type=str, help="Must be one of `['dev', 'prod']`")

    start(parser.parse_args())