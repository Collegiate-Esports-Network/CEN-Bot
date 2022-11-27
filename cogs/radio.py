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
from discord import app_commands

# Logging
import logging
logger = logging.getLogger('radio')


class radio(commands.GroupCog, name='radio'):
    """These are all the radio commands
    """
    def __init__(self, bot: cbot):
        self.bot = bot
        self.queue = dict()
        super().__init__()

    # Bot joins channel user is in
    @app_commands.command(
        name='join',
        description="Has the bot join your voice channel"
    )
    async def radio_join(self, interaction: discord.Interaction) -> None:
        # Get voice client for guild
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        # Test if empty
        if voice_client is None:
            await interaction.user.voice.channel.connect()
            await interaction.response.send_message("Joining...", ephemeral=True)
        else:
            await interaction.response.send_message(f"I am already in use in {voice_client.channel.mention}", ephemeral=True)

    # Bot plays from YouTube
    @app_commands.command(
        name='play',
        description="Plays a URL from YouTube"
    )
    # @app_commands.describe(
    #     URL="YouTube link"
    # )
    async def radio_play(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("I'm sorry, this module is not yet configured", ephemeral=True)

    @app_commands.command(
        name='pause',
        description="Pauses the currently playing audio"
    )
    async def radio_pause(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("I'm sorry, this module is not yet configured", ephemeral=True)

    @app_commands.command(
        name='volume',
        description="Sets the volume level of the bot"
    )
    # @app_commands.describe(
    #     volume="The volume of the music player"
    # )
    async def radio_volume(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("I'm sorry, this module is not yet configured", ephemeral=True)

    # Bot leaves channel
    @app_commands.command(
        name='leave',
        description="Has the bot leave the currently connected voice channel"
    )
    async def radio_leave(self, interaction: discord.Interaction) -> None:
        # Get voice channel
        voice_client = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        # Test if empty, leave if not
        if voice_client is None:
            await interaction.response.send_message("I am not currently connected anywhere!", ephemeral=True)
        else:
            await voice_client.disconnect()
            await interaction.response.send_message("Goodbye!", ephemeral=True)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(radio(bot))