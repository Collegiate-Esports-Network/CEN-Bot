__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "3"
__status__ = "Production"
__doc__ = """Custom Bot class"""

# Python imports
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
log = logging.getLogger('CENBot')

# Init intents
intents = discord.Intents.all()
intents.presences = True
intents.members = True
intents.message_content = True


class cbot(Bot):
    """Custom bot subclass, allowing for creation of paramters in setup.

    Args:
        Bot (discord.ext.commands.Bot): Bot class from discord.ext.commands.Bot.
    """
    def __init__(self) -> None:
        super().__init__(
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.playing, name='big brother'),
            description="Hello! I'm the CEN Bot, a customized bot built and maintained by the Collegiate Esports Network.",
            command_prefix="$$",
            owner_id=0
        )
        self.version = '3.2.0'

    async def setup_hook(self) -> None:
        """Runs setup before the bot completes login
        """
        log.info(f"{self.user.display_name} is connecting...")

        # Create DB connection
        while True:
            try:
                self.db_pool = await asyncpg.create_pool(os.getenv('POSTGRESQL_CONN'))
            except OSError as e:
                log.exception(e)
                break
            except ConnectionFailureError as e:
                log.exception(e)
                break
            else:
                log.info("DB connection established")
                break

        # Load extensions from cogs folder
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                try:
                    await self.load_extension(f"cogs.{file[:-3]}")
                except ExtensionNotFound:
                    log.warning(f"cog '{file[:-3]}' not found")
                except ExtensionError:
                    log.warning(f"cog '{file[:-3]}' not loaded properly")
                else:
                    log.info(f"cog '{file[:-3]}' loaded succesfully")

        # Force command sync
        await self.tree.sync()

    async def on_ready(self) -> None:
        log.info(f"{self.user.display_name} has logged in")
