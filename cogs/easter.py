"""Easter egg commands"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

# Standard library
import random
from logging import getLogger

# Third-party
import discord
from discord.ext import commands

# Internal
from start import CENBot

log = getLogger('CENBot.easter')


class Easter(commands.Cog, name='easter'):
    """These are all the hidden easter egg commands."""
    def __init__(self, bot: CENBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author != self.bot.user and random.randint(1, 100) > 90 and 'crazy' in message.content.lower():
            await message.reply("Crazy? I was crazy once. They locked me in a room. A rubber room. A rubber room with rats, and rats make me crazy.\nCrazy? I was crazy once...")

    @commands.command(
        name="rickroll",
        description="Rickrolls the user.",
        hidden=True
    )
    async def rickroll(self, ctx: commands.Context, *, member: discord.Member) -> None:
        """Rickroll the user mentioned in the message."""
        await ctx.message.delete()
        await ctx.message.channel.send(content=member.mention, file=discord.File("./cogs/assets/audio.mp3"))


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Easter(bot))