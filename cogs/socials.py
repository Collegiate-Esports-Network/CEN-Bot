__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Uses APIs to pull from Twitter and other socials"""

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands

# Logging
import logging
from asyncpg.exceptions import PostgresError
logger = logging.getLogger('socials')


class socials(commands.GroupCog, name='socials'):
    """These are all the logging functions
    """
    def __init__(self, bot: cbot):
        self.bot = bot
        super().__init__()


async def setup(bot: cbot) -> None:
    await bot.add_cog(socials(bot))
