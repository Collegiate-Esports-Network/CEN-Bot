__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = 'Production'
__doc__ = """Utility Functions"""

# Python imports

# Discord imports
import discord
from discord import Interaction
from discord.ext import commands
from discord import app_commands

# youtube-dl imports
from youtube_dl import YoutubeDL

# Custom youtube-dl class
class ydl(YoutubeDL):
    


class radio(commands.GroupCog, name='radio'):
    """These are the bot's radio functions.
    """
    # Init
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.playlist = {}
        super().__init__()
    
    @app_commands.command(
        name='play',
        description='Plays a song'
    )
    @app_commands.describe(
        url='The YouTube url'
    )
    async def radio_play(self, interaction: Interaction):
        # Check if 