__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Functional operations"""

# Python imports
import re

# Custom imports
from helpers.forasync import forasync

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands

# Logging
import logging
log = logging.getLogger('CENBot.functional')


class functional(commands.Cog):
    """Functional interactions
    """
    # Init
    def __init__(self, bot: cbot) -> None:
        self.bot = bot

    # Check for $$time<__>$$ messages to recode into unix (relative to Eastern)
    @commands.Cog.listener()
    @commands.guild_only()
    async def on_message(self, ctx: discord.Message):
        # RegEx Match
        regex_match = re.search(r"(\$\$time<)([0-9][0-9]\/[0-9][0-9]\/[0-9][0-9]\-[0-9][0-9]\:[0-9][0-9]\:[0-9][0-9])(>\$\$)", ctx.content)

        if regex_match:
            # Iterate over matches and replace message content
            async for match in forasync(regex_match):
                print(match)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(functional(bot))