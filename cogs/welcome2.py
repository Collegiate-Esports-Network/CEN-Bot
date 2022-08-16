__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Welcome message functions"""

# Python imports
# import logging

# Discord imports
import discord
from discord.ext import commands
from discord import app_commands


class welcome2(commands.Cog):
    """These are the welcome message functions
    """
    # Init
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # Test command
    @app_commands.command(
        name='test',
        description='Test Command'
    )
    @app_commands.describe(
        msg='Your message here'
    )
    async def test(self, interaction: discord.Interaction, msg: str = None) -> None:
        await interaction.response.send_message(f'You sent {msg}', ephemeral=True)


# Add to bot
async def setup(bot) -> None:
    await bot.add_cog(welcome2(bot))