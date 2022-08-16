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


class welcome(commands.GroupCog, name='welcome'):
    """These are the welcome message functions
    """
    # Init
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    # Sends a message on user join
    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        # Get welcome channel
        welcome_channel = None
        welcome_channel = self.bot.get_channel(welcome_channel)

        # Edit welcome message to mention user
        welcome_message = 'None'
        welcome_message = welcome_message.replace('<new_user>', member.mention)

        # Send welcome message
        # await welcome_channel.send(welcome_message)
    
    # Sets the welcome messsage channel
    @app_commands.command(
        name='setchannel',
        description='Sets the welcome channel'
    )
    @app_commands.describe(
        channel='Discord channel mention'
    )
    @commands.has_role('bot manager')
    async def welcome_setchannel(self, interaction: discord.Interaction, channel: str) -> None:
        await None

    # Sets the welcome message
    @app_commands.command(
        name='setmessage',
        description='Sets the welcome message'
    )
    @app_commands.describe(
        message='The welcome message. Use "<new_user>" to mention the member.'
    )
    @commands.has_role('bot manager')
    async def welcome_setmessage(self, interaction: discord.Interaction, message: str) -> None:
        await None

# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(welcome(bot))