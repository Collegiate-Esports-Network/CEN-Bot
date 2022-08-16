__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """xp Functions"""

# Python imports
from time import time
import random

# Discord imports
import discord
from discord.ext import commands
from discord import app_commands

# MySQL imports

class xp(commands.GroupCog, name='xp'):
    """ These are all functions related to the xp function of the bot.
    """
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_message(self, ctx) -> None:
        # Ignore bot messages or messages from test server
        if self.bot.user == ctx.author or ctx.guild.id == 778306842265911296:
            return
        
        # Generate random number between 1 and 100
        random.seed(round(time() * 1000))
        num = random.randint(1, 100)

        ### GIVE XP TO MESSAGE SENDER ###
    
    @app_commands.command(
        name='xp',
        description='Returns your current xp'
    )
    async def xp_xp(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f'Current num gen is: {time()}')

    @app_commands.command(
        name='leaderboard',
        description='Returns the top 20 xp leaders'
    )
    async def xp_leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f'LEADERBOARD HERE')

# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(xp(bot))