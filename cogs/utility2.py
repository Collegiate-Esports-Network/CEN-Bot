__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Utility Functions"""

# Python imports
import logging
from pathlib import Path

# Discord imports
import discord
from discord.ext import commands
from discord import app_commands

# Get all available cogs
def getcogs():
    allcogs = []
    dir = Path('cogs')
    for entry in dir.iterdir():
        if entry.is_file():
            allcogs.append(entry.stem)
    return allcogs

class utility2(commands.Cog):
    """These are all functions that act as utility to the bot.
    """
    # Init
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    # Reload cogs
    @app_commands.command(
        name='reload',
        description='Reloads an available cog',
        help=f'Reloads one of the following cogs:\n{getcogs()}'
    )
    @commands.is_owner()
    @app_commands.describe(
        cog='The cog to be reloaded'
    )
    async def reload(self, interaction: discord.Interaction, cog: str) -> None:
        if cog.to_lower() == 'all':
            allcogs = getcogs()
            for cog in allcogs:
                await self.bot.reload_extension(f'cogs.{cog}')
            logging.info('All cogs were reloaded')
            interaction.response.send_message('All cogs were reloaded', ephemeral=True)
        else:
            self.bot.reload_extension(f'cogs.{cog}')
            logging.info(f'{cog} was reloaded')
            interaction.response.send_message(f'{cog} was reloaded', ephemeral=True)
    
    # Simple ping command
    @app_commands.command(
        name='ping',
        description='Replies with Pong! (and the bots ping)',
        help='Replies with Pong! (and the bots ping)'
    )
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Pong! ({round(self.bot.latency * 1000, 4)} ms)', ephemeral=True)

### BOT INFO EMBED MISSING ###

# Add to bot
async def setup(bot) -> None:
    await bot.add_cog(utility2(bot))