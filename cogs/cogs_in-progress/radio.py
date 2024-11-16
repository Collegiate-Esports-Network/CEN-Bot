__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "2.0.0"
__status__ = "Production"
__doc__ = """Radio player for discord servers"""

# Python imports
import os
from typing import cast

# Wavelink imports
import wavelink

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
log = logging.getLogger('CENBot.radio')


@commands.guild_only()
class radio(commands.GroupCog, name='radio'):
    """These are all the radio commands
    """
    def __init__(self, bot: cbot):
        self.bot = bot
        super().__init__()

    # Setup radio on cog load
    async def cog_load(self):
        try:
            await wavelink.Pool.connect(client=self.bot, nodes=[wavelink.Node(uri=os.getenv('LAVALINK_ADDRESS'), password=os.getenv('LAVALINK_PASS'))])
        except wavelink.WavelinkException as e:
            log.exception(e)
        else:
            log.info("Lavalink connection established")

    # Bot plays from YouTube
    @app_commands.command(
        name='play',
        description="Queues the song and connects to the user's voice channel if possible"
    )
    @app_commands.describe(query="The Youtube URL or Video Title")
    async def radio_play(self, interaction: discord.Interaction, query: str) -> None:
        # Defer the interaction
        await interaction.response.defer(ephemeral=False, thinking=True)

        # Get player
        player = cast(wavelink.Player, discord.utils.get(self.bot.voice_clients, guild=interaction.guild))

        # Check for player
        if not player:
            try:
                # Get user channel
                channel = interaction.user.voice.channel
            except AttributeError as e:
                log.exception(e)
                await interaction.followup.send("Please join a voice channel first.")
                return
            else:
                # Connect to channel
                player = await channel.connect(cls=wavelink.Player, self_deaf=True)

                # Set player home
                player.home = channel

                # Set autoplay
                player.autoplay = wavelink.AutoPlayMode.enabled
        elif player.home != interaction.user.voice.channel:  # Check if it's already attached to a channel
            await interaction.followup.send(f"Songs are already playing in {player.home.mention}")
            return

        # Get the track
        try:
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
            track = tracks[0]
        except IndexError as e:
            log.exception(e)
            await interaction.followup.send(f"There was an error getting ``{query}``, {interaction.user.mention}. Please try again.")
            return

        # Add track to queue
        await player.queue.put_wait(track)

        # Check if already playing
        if not player.playing:
            # Play
            player.play(player.queue.get(), volume=50)

    # Bot leaves channel
    @app_commands.command(
        name='leave',
        description="Has the bot leave the currently connected voice channel"
    )
    async def radio_leave(self, interaction: discord.Interaction) -> None:
        # Get player
        player = cast(wavelink.Player, discord.utils.get(self.bot.voice_clients, guild=interaction.guild))

        # Check for player
        if not player:
            log.error("No player found")
            return
        else:
            try:
                await player.disconnect()
            except wavelink.WavelinkException as e:
                log.exception(e)
                await interaction.response.send_message("There was an error disconnecting, please try again.", ephemeral=False)
                return

        await interaction.response.send_message("Disconnected.")

    # Control commands
    @app_commands.command(
        name='play_pause',
        description="Toggles the state of the radio"
    )
    async def radio_toggle(self, interaction: discord.Interaction) -> None:
        # Get player if it exists
        player = cast(wavelink.Player, discord.utils.get(self.bot.voice_clients, guild=interaction.guild))

        # Check for player
        if not player:
            log.error("No player found")
            return
        else:
            try:
                await player.pause(False)
            except wavelink.WavelinkException as e:
                log.exception(e)
                await interaction.response.send_message("There was an error resuming your track, please try again.", ephemeral=True)
                return
            else:
                await interaction.response.send_message(f"{player.current} | {player.playing}")

    @app_commands.command(
        name='skip',
        description="Skips the currently playing track"
    )
    async def radio_skip(self, interaction: discord.Interaction) -> None:
        # Get player
        player = cast(wavelink.Player, discord.utils.get(self.bot.voice_clients, guild=interaction.guild))

        # Check for player
        if not player:
            log.error("No player found")
            return

        # Check if user is in same vc as bot
        if interaction.user.voice.channel != player.channel:
            await interaction.response.send_message("You must be in the same Voice Channel as the Bot to use this command.", ephemeral=True)
            return

        # Skip track
        await player.skip()
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

        # Get player
        player = cast(wavelink.Player, discord.utils.get(self.bot.voice_clients, guild=interaction.guild))

        # Check for player
        if not player:
            log.error("No player found")
            return

        # Check if user is in same vc as bot
        if interaction.user.voice.channel != player.channel:
            await interaction.response.send_message("You must be in the same Voice Channel as the Bot to use this command.", ephemeral=True)
            return

        # Adjust volume
        try:
            await player.set_volume(volume)
        except wavelink.WavelinkException as e:
            log.exception(e)
            await interaction.response.send_message("There was an error setting the volume, please try again.", ephemeral=True)
            return
        else:
            await interaction.response.send_message(f"Volume set to {volume}.")

    # QOL
    # Edit embed
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        # Get player
        player = payload.player

        # Check for player
        if not player:
            log.error("No player found")
            return
        else:
            # Build embed
            embed = discord.Embed(title="Now Playing")
            embed.color = discord.Color.from_str("#2374A5")
            if payload.original and payload.original.recommended:
                embed.description += f"\n\n`This track was recommended via {payload.track.source}`"
            else:
                embed.description = f"**{payload.track.title}** from *{payload.track.album.name} by `{payload.track.author}`"

            # Set embed art
            if payload.track.artwork:
                embed.set_image(url=payload.track.artwork)

            # Set "Next Up" section
            i = 0
            for track in player.queue:
                if track.recommended:
                    embed.add_field(name="Next Up", value=f"{track.title} | AutoPlay")
                else:
                    embed.add_field(name="Next Up", value=f"{track.title}")
                if i >= 5:
                    break

        if hasattr(player, "embed"):
            player.embed.edit(embed=embed)
        else:
            player.embed = await player.channel.send(embed=embed)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(radio(bot))