__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '3'
__status__ = 'Production'
__doc__ = """Custom Bot class"""

# Python imports
from asyncio import sleep
import os

# Discord imports
import discord
from discord.ext.commands import Bot

# Database imports
import asyncpg

# Logging
import logging
from asyncpg.exceptions import ConnectionFailureError
from discord.ext.commands import ExtensionError, ExtensionNotFound
logger = logging.getLogger('CENBot')

# Init intents
intents = discord.Intents.all()
intents.presences = True
intents.members = True
intents.message_content = True


class cbot(Bot):
    """Custom bot subclass, allowing for creation of paramters in setup

    Args:
        Bot (discord.ext.commands.Bot): Bot class from discord.ext.commands.Bot
    """
    def __init__(self) -> None:
        super().__init__(
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.playing, name='big brother'),
            description="Hello! I'm the CEN Bot, a customized bot built and maintained by the Collegiate Esports Network.",
            command_prefix="$$"
        )
        self.version = '3.0.0'

    async def setup_hook(self) -> None:
        """Runs setup before the bot completes login
        """
        logger.info(f"{self.user.display_name} is connecting...")

        # Create DB connection
        while True:
            try:
                self.db_pool = await asyncpg.create_pool(os.getenv('POSTGRESQL_CONN'))
            except ConnectionFailureError as e:
                logger.exception("Error connecting to database, retrying in 60 seconds")
                logger.error(e)
                sleep(60)
            else:
                logger.info("DB connection established")
                break

        # Load extensions from cogs folder
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                try:
                    await self.load_extension(f"cogs.{file[:-3]}")
                except ExtensionNotFound as e:
                    logger.warning(f"cog '{e.name}' not found")
                except ExtensionError as e:
                    logger.warning(f"cog {e.name} not loaded properly")
                else:
                    logger.info(f"cog '{file[:-3]}' loaded succesfully")

        # Force command sync
        await self.tree.sync()

    async def on_ready(self) -> None:
        logger.info(f"{self.user.display_name} has logged in")