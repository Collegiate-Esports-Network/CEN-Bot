__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Logs activity in discord servers"""

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands


class easter(commands.Cog, name='easter'):
    """These are all the hidden easter egg commands
    """
    def __init__(self, bot: cbot):
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_message(self, ctx: discord.Message) -> None:
        if ctx.author != self.bot.user and 'crazy' in ctx.content:
            await ctx.reply("Crazy? I was crazy once. They locked me in a room. A rubber room. A rubber room with rats, and rats make me crazy.\nCrazy? I was crazy once...")


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(easter(bot))