__author__ = 'Chris Taylor'
__copyright__ = 'Copyright CEN'
__credits__ = 'Chris Taylor'
__version__ = '0.0.0'
__status__ = 'Development'
__doc__ = """Starboard functions"""

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
from asyncpg.exceptions import PostgresError
logger = logging.getLogger('starboard')


class starboard(commands.GroupCog, name='starboard'):
    """These are the starboard functions.
    """
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(starboard(bot))