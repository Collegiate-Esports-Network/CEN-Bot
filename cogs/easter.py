__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Easter Eggies"""

# Python imports
import random
from time import time

# Discord imports
from start import cenbot
import discord
from discord.ext import commands

# Logging
import logging
log = logging.getLogger('CENBot.easter')


class easter(commands.Cog, name='easter'):
    """These are all the hidden easter egg commands
    """
    def __init__(self, bot: cenbot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, ctx: commands.Context) -> None:
        # Choose a random number
        random.seed(round(time() * 1000))
        num = random.randint(1, 100)

        if ctx.author != self.bot.user and num > 90 and 'crazy' in ctx.message.content.lower():
            await ctx.reply("Crazy? I was crazy once. They locked me in a room. A rubber room. A rubber room with rats, and rats make me crazy.\nCrazy? I was crazy once...")

    @commands.command(
        name="rickroll",
        description="Rickrolls the user.",
        hidden=True
    )
    async def rickroll(self, ctx: commands.Context, *, member: discord.Member) -> None:
        """Rickroll the user mentioned in the message."""
        await ctx.message.delete()
        await ctx.message.channel.send(content=member.mention, file=discord.File("./cogs/assets/audio.mp3"))


# Add to bot
async def setup(bot: cenbot) -> None:
    await bot.add_cog(easter(bot))