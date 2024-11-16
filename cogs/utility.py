__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "3.0.0"
__status__ = "Production"
__doc__ = """Utility Functions"""

# Python imports
import sys
import random
from datetime import datetime
import pytz

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
log = logging.getLogger('CENBot.utility')


@app_commands.guild_only()
class utility(commands.Cog):
    """Simple commands for all.
    """
    # Init
    def __init__(self, bot: cbot) -> None:
        self.bot = bot

    @app_commands.command(
        name='ping',
        description="Replies with Pong! (and the bots ping)",
    )
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! ({round(self.bot.latency * 1000, 4)} ms)", ephemeral=True)

    @app_commands.command(
        name='about',
        description="Returns the current bot information",
    )
    async def about(self, interaction: discord.Interaction) -> None:
        # Create embed
        embed = discord.Embed(title='Bot Info', description="Here is the most up-to-date information on the bot.", color=0x2374A5)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        embed.add_field(name="Bot Version:", value=self.bot.version)
        embed.add_field(name="Python Version:", value=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        embed.add_field(name="Discord.py Version:", value=discord.__version__)
        embed.add_field(name="Written By:", value="[Justin Panchula](https://github.com/JustinPanchula) and [Chris Taylor](https://github.com/Taylo5ce)", inline=False)
        embed.add_field(name="Server Information:", value=f"This bot is in {len(self.bot.guilds)} servers watching over \
                                                            {len(set(self.bot.get_all_members()))-len(self.bot.guilds)} members.", inline=False)
        embed.set_footer(text=f"Information requested by: {interaction.user}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name='flip',
        description="Flips a coin"
    )
    async def flip(self, interaction: discord.Interaction) -> None:
        # Choose heads or tails
        random.seed(round(discord.utils.utcnow() * 1000))
        heads = random.randint(0, 1)

        if heads:
            await interaction.response.send_message(f"{interaction.user.mention} the coin is Heads.")
        else:
            await interaction.response.send_message(f"{interaction.user.mention} the coin is Tails.")

    @app_commands.command(
        name='utc',
        description="Converts the input (eastern time) to a relative timestamp"
    )
    async def timestamp(self, interaction: discord.Interaction, year: int, month: int, day: int, hour: int, minute: int) -> None:
        try:
            user_time = datetime(year, month, day, hour, minute+4, 0, 0, pytz.timezone('US/Eastern'))
        except ValueError as e:
            await interaction.response.send_message(f"{e}", ephemeral=True)
            return

        await interaction.response.send_message(f"Relative datetime: ``<t:{int(user_time.timestamp())}:R>``", ephemeral=True)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(utility(bot))
