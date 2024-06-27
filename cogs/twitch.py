__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '1.1.0'
__status__ = 'Production'
__doc__ = """Uses Twitch's API to pull live feeds from Twitch"""

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands, tasks
from discord import app_commands


# Logging
import logging
from asyncpg.exceptions import PostgresError
log = logging.getLogger('CENBot.twitch')

@app_commands.guild_only()
class twitch(commands.GroupCog, name='twitch'):
    """These are all the Twitch function.
    """
    def __init__(self, bot: cbot):
        self.bot = bot
        super().__init__()


# Check Twitch every 1m
@tasks.loop(minutes=1)
async def check_twitch(self):
    # Annouce run
    log.info("Checking Twitch for new livestreams...")

    # Annouce completion
    log.info("Finished checking Twitch for new livestreams")


async def setup(bot: cbot) -> None:
    await bot.add_cog(twitch(bot))