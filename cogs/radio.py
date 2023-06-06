__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Logs activity in discord servers"""

# Python imports
import os
import datetime

# Wavelink imports
import wavelink
# from wavelink.ext import spotify

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
        super().__init__()

    def get_vc(self, guild: discord.Guild) -> wavelink.Player:
        """Helper function to grab guild voice clients as Wavelink Players

        Args:
            guild (discord.Guild): the discord Guild

        Returns:
            wavelink.Player: the wavelink player
        """
        return discord.utils.get(self.bot.voice_clients, guild=guild)

    # Setup radio on cog load
    async def cog_load(self):
        try:
            await wavelink.NodePool.connect(client=self.bot, nodes=[wavelink.Node(uri=os.getenv('LAVALINK_ADDRESS'), password=os.getenv('LAVALINK_PASS'))])
        except wavelink.WavelinkException as e:
            logger.exception(e)
        else:
            logger.info("Lavalink connection established")

    # Bot plays from YouTube
    @app_commands.command(
        name='play',
        description="Plays a song from YouTube, or adds one to the queue if one is already playing"
    )
    async def radio_play(self, interaction: discord.Interaction, search: str) -> None:
        if discord.utils.get(self.bot.voice_clients, guild=interaction.guild) is None:  # Create the player and connect
            try:
                channel = interaction.user.voice.channel
            except AttributeError as e:
                logger.exception(e)
                await interaction.response.send_message("Please join a voice channel first!", ephemeral=True)
            else:
                await channel.connect(cls=wavelink.Player, self_deaf=True)

        # Get the track
        track = await wavelink.YouTubeTrack.search(search, return_first=True)

        # Get the player
        player = self.get_vc(interaction.guild)
        player.autoplay = True

        # Play the track, or add to queue
        if player.is_playing():
            player.queue.put(track)
            await interaction.response.send_message(f"Added ``{track.title}`` to the queue.")
        else:
            await player.play(track)
            await interaction.response.send_message(f"Playing ``{track.title}``")

    # Bot leaves channel
    @app_commands.command(
        name='leave',
        description="Has the bot leave the currently connected voice channel"
    )
    async def radio_leave(self, interaction: discord.Interaction) -> None:
        # Get player
        player = self.get_vc(interaction.guild)

        if player.is_connected():
            try:
                await player.disconnect()
            except wavelink.WavelinkException as e:
                logger.exception(e)
                await interaction.response.send_message("There was an error disconnecting, please try again.", ephemeral=True)
        # Clear the queue
        player.queue.reset()

    # Control commands
    @app_commands.command(
        name='resume',
        description="Resumes the currently paused audio"
    )
    async def radio_resume(self, interaction: discord.Interaction) -> None:
        # Get the player
        player = self.get_vc(interaction.guild)

        if player.is_paused():
            try:
                await player.resume()
            except wavelink.WavelinkException as e:
                logger.exception(e)
                await interaction.response.send_message("There was an error resuming your track, please try again.", ephemeral=True)
            else:
                await interaction.response.send_message(f"{player.current} | Resumed")

    @app_commands.command(
        name='pause',
        description="Pauses the currently playing audio"
    )
    async def radio_pause(self, interaction: discord.Interaction) -> None:
        # Get the player
        player = self.get_vc(interaction.guild)

        if player.is_playing():
            try:
                await player.pause()
            except wavelink.WavelinkException as e:
                logger.exception(e)
                await interaction.response.send_message("There was an error pausing your track, please try again.", ephemeral=True)
            else:
                await interaction.response.send_message(f"{player.current} | Paused")

    @app_commands.command(
        name='skip',
        description="Skips the currently playing track"
    )
    async def radio_skip(self, interaction: discord.Interaction) -> None:
        # Get the player
        player = self.get_vc(interaction.guild)

        # Check if user is in same vc as bot
        if interaction.user.voice.channel != player.channel:
            await interaction.response.send_message("You must be in the same Voice Channel as the Bot to use this command.", ephemeral=True)
            return

        # Skip track
        await player.seek(player.current.duration)  # FIXME: Does not skip?
        await interaction.response.send_message(f"``{player.current.title}`` skipped.", ephemeral=False)

    @app_commands.command(
        name='volume',
        description="Sets the volume level of the bot"
    )
    @app_commands.describe(
        volume="The volume of the music player"
    )
    async def radio_volume(self, interaction: discord.Interaction, volume: int) -> None:
        # Keep volume between 0 and 100
        if volume > 100:
            volume = 100
        elif volume < 0:
            volume = 0

        # Get the player
        player = self.get_vc(interaction.guild)

        # Check if user is in same vc as bot
        if interaction.user.voice.channel != player.channel:
            await interaction.response.send_message("You must be in the same Voice Channel as the Bot to use this command.", ephemeral=True)
            return

        # Adjust volume
        try:
            await player.set_volume(volume)
        except wavelink.WavelinkException as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error setting the volume, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Volume set to {volume}.")

    # QOL
    @app_commands.command(
        name='queue',
        description="Displays the radio queue"
    )
    async def radio_queue(self, interaction: discord.Interaction) -> None:
        # Get the player
        player = self.get_vc(interaction.guild)

        if player is not None:
            # Create embed
            embed = discord.Embed(
                title="Radio Queue",
                color=discord.Colour.blurple())

            # Add current track
            embed.add_field(name="Currently Playing", value=f"{player.current.title} | {datetime.timedelta(milliseconds=player.current.position)}/{datetime.timedelta(milliseconds=player.current.duration)}")

            # Populate
            i = 1
            for track in player.queue:
                if i == 1:
                    embed.add_field(name="Up Next", value=f"{track.title} | {datetime.timedelta(milliseconds=track.duration)}", inline=False)
                else:
                    embed.add_field(name=f"#{i}", value=f"{track.title} | {datetime.timedelta(milliseconds=track.duration)}", inline=False)
                i += 1

            # Send embed
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("The queue is currently empty. Use ``/radio play`` to search for one.", ephemeral=True)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(radio(bot))