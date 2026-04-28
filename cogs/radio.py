"""Audio playback from YouTube URLs via Lavalink and Wavelink."""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = ["Justin Panchula", "Claude"]
__version__ = "3.0.0"
__status__ = "Development"

# Standard library
import asyncio
import contextlib
import os
from dataclasses import dataclass
from logging import getLogger

# Third-party
import discord
import wavelink
from discord import app_commands
from discord.ext import commands, tasks

# Internal
from start import CENBot
from utils import BRAND_COLOR, format_duration

log = getLogger('CENBot.radio')


@dataclass
class GuildState:
    """Per-guild radio playback state.

    :param player: the active Wavelink player, or ``None`` when disconnected
    :param current: the currently playing track object with requester metadata
    :param volume: playback volume as a percentage (0-100)
    :param controls_message: the pinned controls panel message, or ``None``
    """

    player: wavelink.Player | None = None
    current: wavelink.Playable | None = None
    volume: int = 100
    controls_message: discord.Message | None = None


class VolumeModal(discord.ui.Modal, title='Set Volume'):
    """Modal for adjusting playback volume (0-100)."""

    volume_input = discord.ui.TextInput(
        label='Volume (0-100)',
        placeholder='75',
        min_length=1,
        max_length=3,
    )

    def __init__(self, cog: 'Radio', guild_id: int) -> None:
        """Initialise with a back-reference to the cog and guild.

        :param cog: the Radio cog instance
        :type cog: Radio
        :param guild_id: the guild's ID
        :type guild_id: int
        """
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Apply the submitted volume value to the active player.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            vol = int(self.volume_input.value)
        except ValueError:
            await interaction.response.send_message("Volume must be a whole number between 0 and 100.", ephemeral=True)
            return
        if not 0 <= vol <= 100:
            await interaction.response.send_message("Volume must be between 0 and 100.", ephemeral=True)
            return

        state = self.cog._get_state(self.guild_id)
        state.volume = vol
        player = state.player

        await interaction.response.defer()

        if player and player.connected:
            try:
                await player.set_volume(vol)
            except Exception as e:
                log.warning(f"Volume update failed in guild {self.guild_id}: {e}")

        await self.cog._update_controls(self.guild_id)


class RadioControlsView(discord.ui.View):
    """Persistent voice-channel controls panel for the Radio cog."""

    def __init__(self, cog: 'Radio', guild_id: int) -> None:
        """Initialise the controls view for a guild.

        :param cog: the Radio cog instance
        :type cog: Radio
        :param guild_id: the guild's ID
        :type guild_id: int
        """
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Allow interaction only from users currently in the bot's voice channel.

        :param interaction: the incoming interaction
        :type interaction: discord.Interaction
        :returns: True if the user may use these controls
        :rtype: bool
        """
        state = self.cog._get_state(self.guild_id)
        player = state.player

        if not player or not player.connected or not player.channel:
            await interaction.response.send_message("The bot is not in a voice channel.", ephemeral=True)
            return False

        if not interaction.user.voice or interaction.user.voice.channel != player.channel:
            await interaction.response.send_message("You must be in the same voice channel to use these controls.", ephemeral=True)
            return False

        return True

    @discord.ui.button(emoji='⏯', style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Toggle between paused and playing.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param button: the triggered button
        :type button: discord.ui.Button
        """
        state = self.cog._get_state(self.guild_id)
        player = state.player

        if player and player.playing:
            await player.pause(True)
        elif player and player.paused:
            await player.pause(False)

        await interaction.response.defer()
        await self.cog._sync_voice_channel_status(self.guild_id)
        await self.cog._update_controls(self.guild_id)

    @discord.ui.button(emoji='⏭', style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Skip the current track and advance the queue.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param button: the triggered button
        :type button: discord.ui.Button
        """
        state = self.cog._get_state(self.guild_id)
        player = state.player

        if not player or not (player.playing or player.paused):
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return

        await player.skip(force=True)
        await interaction.response.defer()

    @discord.ui.button(emoji='⏹', style=discord.ButtonStyle.danger, row=0)
    async def stop_playback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Stop playback, clear the queue, and disconnect the bot.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param button: the triggered button
        :type button: discord.ui.Button
        """
        state = self.cog._get_state(self.guild_id)
        player = state.player

        if not player:
            await interaction.response.send_message("The bot is not in a voice channel.", ephemeral=True)
            return

        old_channel = player.channel
        player.queue.clear()
        state.current = None

        await self.cog._set_voice_channel_status(self.guild_id, old_channel, None)
        await player.disconnect()
        state.player = None

        await interaction.response.defer()
        await self.cog._update_controls(self.guild_id)

    @discord.ui.button(emoji='🔊', label='Volume', style=discord.ButtonStyle.secondary, row=0)
    async def volume(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Open the volume input modal.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param button: the triggered button
        :type button: discord.ui.Button
        """
        await interaction.response.send_modal(VolumeModal(self.cog, self.guild_id))


@app_commands.guild_only()
class Radio(commands.GroupCog, name="radio"):
    """Audio playback from YouTube via Lavalink."""

    def __init__(self, bot: CENBot) -> None:
        """Initialise the cog and prepare an empty per-guild state registry.

        :param bot: the bot instance
        :type bot: CENBot
        """
        self.bot = bot
        self._states: dict[int, GuildState] = {}
        self._node_ready = asyncio.Event()
        self._node_status_message = "Lavalink is not connected."
        super().__init__()

    async def cog_load(self) -> None:
        """Connect to Lavalink if configured and start the controls ticker."""
        await self._ensure_node()
        self._controls_ticker.start()

    async def cog_unload(self) -> None:
        """Disconnect players owned by this cog and stop the controls ticker."""
        self._controls_ticker.stop()

        for state in self._states.values():
            player = state.player
            if player and player.connected:
                with contextlib.suppress(Exception):
                    await self._set_voice_channel_status(player.guild.id, player.channel, None)
                    await player.disconnect()

    def _get_state(self, guild_id: int) -> GuildState:
        """Return the GuildState for a guild, creating one if needed.

        :param guild_id: the guild's ID
        :type guild_id: int
        :returns: the guild's radio state
        :rtype: GuildState
        """
        if guild_id not in self._states:
            self._states[guild_id] = GuildState()
        return self._states[guild_id]

    async def _wait_for_node(self, node: wavelink.Node, timeout: float = 10.0) -> bool:
        """Poll until the node is CONNECTED or the timeout expires.

        :param node: the node to wait on
        :type node: wavelink.Node
        :param timeout: maximum seconds to wait
        :type timeout: float
        :returns: True if the node became CONNECTED within the timeout
        :rtype: bool
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while node.status != wavelink.NodeStatus.CONNECTED:
            if loop.time() >= deadline:
                return False
            await asyncio.sleep(0.1)
        return True

    async def _ensure_node(self) -> bool:
        """Ensure a Lavalink node is connected and ready for playback.

        :returns: True if a node is available for playback
        :rtype: bool
        """
        try:
            node = wavelink.Pool.get_node()
            if node.status == wavelink.NodeStatus.CONNECTED:
                self._node_ready.set()
                self._node_status_message = "Lavalink is connected."
                return True
            if not await self._wait_for_node(node):
                log.warning("Lavalink node did not become ready within timeout")
                self._node_ready.clear()
                self._node_status_message = "Radio is still waiting for Lavalink to finish connecting."
                return False
            self._node_ready.set()
            self._node_status_message = "Lavalink is connected."
            return True
        except Exception:
            pass

        if not (os.getenv("LAVALINK_URI") and os.getenv("LAVALINK_PASSWORD")):
            log.warning("Lavalink is not configured. Set LAVALINK_URI and LAVALINK_PASSWORD to enable /radio.")
            self._node_ready.clear()
            self._node_status_message = "Radio is unavailable because Lavalink is not configured."
            return False

        try:
            node = wavelink.Node(
                identifier=os.getenv("LAVALINK_IDENTIFIER"),
                uri=os.getenv("LAVALINK_URI"),
                password=os.getenv("LAVALINK_PASSWORD"),
            )
            await wavelink.Pool.connect(nodes=[node], client=self.bot)
        except Exception as e:
            log.warning(f"Lavalink connection failed: {e}")
            self._node_ready.clear()
            self._node_status_message = "Radio is unavailable because Lavalink could not be reached."
            return False

        if not await self._wait_for_node(node):
            log.warning("Lavalink node did not become ready within timeout")
            self._node_ready.clear()
            self._node_status_message = "Radio is still waiting for Lavalink to finish connecting."
            return False

        self._node_ready.set()
        self._node_status_message = "Lavalink is connected."
        return True

    def _node_unavailable_message(self) -> str:
        """Return a user-facing message for the current Lavalink state.

        :returns: a concise playback-unavailable message
        :rtype: str
        """
        return self._node_status_message

    async def _ensure_player(self, guild_id: int, channel: discord.VoiceChannel) -> wavelink.Player | None:
        """Return a connected player for the given guild and voice channel.

        :param guild_id: the guild's ID
        :type guild_id: int
        :param channel: the channel to join or move into
        :type channel: discord.VoiceChannel
        :returns: a connected Wavelink player, or None on failure
        :rtype: wavelink.Player | None
        """
        state = self._get_state(guild_id)
        player = state.player

        if player and player.connected:
            if player.channel != channel:
                old_channel = player.channel
                await player.move_to(channel)
                await self._set_voice_channel_status(guild_id, old_channel, None)
                await self._sync_voice_channel_status(guild_id)
            return player

        # Clear any stale Discord voice client before connecting to avoid gateway timeout.
        guild = self.bot.get_guild(guild_id)
        if guild and guild.voice_client:
            with contextlib.suppress(Exception):
                await guild.voice_client.disconnect(force=True)

        try:
            player = await channel.connect(cls=wavelink.Player, self_deaf=True)
        except Exception as e:
            log.warning(f"Voice connection failed in guild {guild_id}: {e}")
            return None

        player.autoplay = wavelink.AutoPlayMode.partial
        state.player = player

        try:
            await player.set_volume(state.volume)
        except Exception as e:
            log.warning(f"Initial volume set failed in guild {guild_id}: {e}")

        return player

    async def _start_track(self, guild_id: int, track: wavelink.Playable) -> bool:
        """Begin playback of a track on the guild's player.

        :param guild_id: the guild's ID
        :type guild_id: int
        :param track: the track to play
        :type track: wavelink.Playable
        :returns: True if playback started successfully
        :rtype: bool
        """
        state = self._get_state(guild_id)
        player = state.player

        if not player or not player.connected:
            return False

        state.current = track
        try:
            await player.play(track, volume=state.volume)
        except wavelink.LavalinkException as e:
            log.warning(f"Failed to start track in guild {guild_id}: {e}")
            state.current = None
            return False

        await self._sync_voice_channel_status(guild_id)
        await self._update_controls(guild_id)
        return True

    async def _set_voice_channel_status(
        self,
        guild_id: int,
        channel: discord.VoiceChannel | discord.StageChannel | None,
        status: str | None,
    ) -> None:
        """Apply a voice channel status update to a specific channel.

        :param guild_id: the guild's ID
        :type guild_id: int
        :param channel: the voice or stage channel to update
        :type channel: discord.VoiceChannel | discord.StageChannel | None
        :param status: the status text to set, or None to clear it
        :type status: str | None
        """
        if channel is None:
            return
        try:
            await channel.edit(status=status)
        except discord.Forbidden as e:
            log.warning(f"Voice channel status update forbidden in guild {guild_id}: {e}")
        except discord.HTTPException as e:
            log.warning(f"Voice channel status update failed in guild {guild_id}: {e}")

    async def _sync_voice_channel_status(self, guild_id: int) -> None:
        """Update the connected voice channel status from the current guild state.

        :param guild_id: the guild's ID
        :type guild_id: int
        """
        state = self._get_state(guild_id)
        player = state.player
        current = state.current

        if current and player and player.connected:
            if player.paused:
                status: str | None = f"⏸ {current.title}"
            elif player.playing:
                status = f"▶ {current.title}"
            else:
                status = None
        else:
            status = None

        channel = player.channel if player and player.channel else None
        await self._set_voice_channel_status(guild_id, channel, status)

    def _controls_embed(self, guild_id: int) -> discord.Embed:
        """Build the radio controls embed showing track, progress, queue, and volume.

        :param guild_id: the guild's ID
        :type guild_id: int
        :returns: the controls embed
        :rtype: discord.Embed
        """
        state = self._get_state(guild_id)
        player = state.player
        current = state.current
        embed = discord.Embed(title="🎵 Radio Controls", color=BRAND_COLOR)

        if current:
            duration_seconds = current.length // 1000 if current.length else 0
            elapsed_seconds = player.position // 1000 if player else 0
            elapsed_seconds = max(0, min(duration_seconds, elapsed_seconds)) if duration_seconds else elapsed_seconds

            if duration_seconds:
                bar_len = 15
                filled = round(bar_len * elapsed_seconds / duration_seconds)
                bar = '▓' * filled + '░' * (bar_len - filled)
                progress = f"`{bar}` {format_duration(elapsed_seconds)} / {format_duration(duration_seconds)}"
            else:
                progress = "Live stream or unknown duration"

            requester = getattr(current, 'requester', None)
            requester_text = requester.mention if requester else "Unknown requester"
            source_link = f"[Source]({current.uri})" if current.uri else "Source unavailable"
            status = '⏸ Paused' if player and player.paused else '▶ Playing'

            embed.add_field(
                name=f"{status} — {current.title}",
                value=f"{source_link} • Requested by {requester_text}\n{progress}",
                inline=False,
            )
        else:
            embed.add_field(
                name="Nothing playing",
                value="Use `/radio play <url>` to queue a track.",
                inline=False,
            )

        if player and player.queue:
            lines = [
                f"{i}. **{track.title}** [{format_duration(track.length // 1000) if track.length else 'Live'}]"
                for i, track in enumerate(player.queue, 1)
            ]
            overflow = f"\n*...and {len(player.queue) - 5} more*" if len(player.queue) > 5 else ""
            embed.add_field(
                name=f"Up Next — {len(player.queue)} track(s)",
                value='\n'.join(lines[:5]) + overflow,
                inline=False,
            )

        embed.set_footer(text=f"🔊 Volume: {state.volume}%")
        return embed

    async def _update_controls(self, guild_id: int) -> None:
        """Edit the pinned controls message with a refreshed embed.

        :param guild_id: the guild's ID
        :type guild_id: int
        """
        state = self._get_state(guild_id)
        if not state.controls_message:
            return
        try:
            await state.controls_message.edit(embed=self._controls_embed(guild_id))
        except discord.NotFound:
            state.controls_message = None
        except discord.HTTPException as e:
            log.warning(f"Controls update failed for guild {guild_id}: {e}")

    async def _send_controls(self, channel: discord.abc.Messageable, guild_id: int) -> None:
        """Send a new controls panel to the given channel, deleting any previous one.

        :param channel: the channel to send the panel to
        :type channel: discord.abc.Messageable
        :param guild_id: the guild's ID
        :type guild_id: int
        """
        state = self._get_state(guild_id)

        if state.controls_message:
            with contextlib.suppress(discord.NotFound):
                await state.controls_message.delete()
            state.controls_message = None

        msg = await channel.send(embed=self._controls_embed(guild_id), view=RadioControlsView(self, guild_id))
        state.controls_message = msg

    @tasks.loop(seconds=5)
    async def _controls_ticker(self) -> None:
        """Refresh all active controls panels every 5 seconds while audio is playing."""
        for guild_id, state in list(self._states.items()):
            player = state.player
            if state.controls_message and player and player.playing:
                await self._update_controls(guild_id)

    @_controls_ticker.before_loop
    async def _before_ticker(self) -> None:
        """Wait for the bot to be ready before starting the ticker."""
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        """Log when the Lavalink node is ready and clear stale player state.

        :param payload: the Wavelink node-ready payload
        :type payload: wavelink.NodeReadyEventPayload
        """
        log.info(f"Lavalink node {payload.node.identifier!r} connected (resumed={payload.resumed})")
        self._node_ready.set()
        self._node_status_message = "Lavalink is connected."
        if not payload.resumed:
            for state in self._states.values():
                state.player = None
                state.current = None

    @commands.Cog.listener()
    async def on_wavelink_node_disconnected(self, payload: wavelink.NodeDisconnectedEventPayload) -> None:
        """Track node disconnects so commands can report a precise failure reason.

        :param payload: the Wavelink node-disconnected payload
        :type payload: wavelink.NodeDisconnectedEventPayload
        """
        log.warning(f"Lavalink node {payload.node.identifier!r} disconnected")
        self._node_ready.clear()
        self._node_status_message = "Radio is temporarily unavailable because the Lavalink node disconnected."

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        """Refresh UI state when a track starts.

        :param payload: the Wavelink track-start payload
        :type payload: wavelink.TrackStartEventPayload
        """
        player = payload.player
        if not player or not player.guild:
            return

        state = self._get_state(player.guild.id)
        state.player = player
        state.current = payload.original or payload.track
        await self._sync_voice_channel_status(player.guild.id)
        await self._update_controls(player.guild.id)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        """Clear the current track from state when playback ends.

        Queue advancement is handled automatically by ``AutoPlayMode.partial``.

        :param payload: the Wavelink track-end payload
        :type payload: wavelink.TrackEndEventPayload
        """
        player = payload.player
        if not player or not player.guild:
            return

        state = self._get_state(player.guild.id)
        state.current = None
        await self._sync_voice_channel_status(player.guild.id)
        await self._update_controls(player.guild.id)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload) -> None:
        """Log track exceptions; queue advancement is handled by ``AutoPlayMode.partial``.

        :param payload: the Wavelink track-exception payload
        :type payload: wavelink.TrackExceptionEventPayload
        """
        player = payload.player
        if not player or not player.guild:
            return

        log.warning(f"Playback exception in guild {player.guild.id}: {payload.exception}")

    @app_commands.command(name='play', description="Add a YouTube URL to the queue")
    @app_commands.describe(url="YouTube video URL")
    async def play(self, interaction: discord.Interaction, url: str) -> None:
        """Queue a YouTube URL and start playback if no active session exists.

        Connects to the user's voice channel if the bot is not already there,
        and sends the controls panel to the voice channel on first connect.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param url: the YouTube video URL
        :type url: str
        """
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You must be in a voice channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if not await self._ensure_node():
            await interaction.followup.send(self._node_unavailable_message(), ephemeral=True)
            return

        guild_id = interaction.guild.id
        voice_channel = interaction.user.voice.channel
        state = self._get_state(guild_id)
        first_connect = state.player is None or not state.player.connected

        player = await self._ensure_player(guild_id, voice_channel)
        if not player:
            await interaction.followup.send("Could not connect to the voice channel.", ephemeral=True)
            return

        try:
            results = await wavelink.Playable.search(url)
        except Exception as e:
            log.warning(f"Track search failed for query {url!r}: {e}")
            await interaction.followup.send("Could not retrieve audio from that URL.", ephemeral=True)
            return

        if isinstance(results, wavelink.Playlist) or not results:
            await interaction.followup.send("Could not retrieve audio from that URL.", ephemeral=True)
            return

        track = results[0]
        setattr(track, 'requester', interaction.user)

        if player.playing or player.paused or state.current or player.queue:
            player.queue.put(track)
            await interaction.followup.send(
                f"Added to queue (position {len(player.queue)}): **{track.title}** "
                f"[{format_duration(track.length // 1000) if track.length else 'Live'}]",
                ephemeral=True,
            )
            await self._update_controls(guild_id)
        else:
            if not await self._start_track(guild_id, track):
                await interaction.followup.send("Failed to start playback. The Lavalink session may have expired — please try again.", ephemeral=True)
                return
            await interaction.followup.send(
                f"Now playing: **{track.title}** "
                f"[{format_duration(track.length // 1000) if track.length else 'Live'}]",
                ephemeral=True,
            )

        if first_connect:
            await self._send_controls(voice_channel, guild_id)

    @app_commands.command(name='controls', description="Show the radio controls panel in this channel")
    async def controls(self, interaction: discord.Interaction) -> None:
        """Re-summon the radio controls panel in the current channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        state = self._get_state(interaction.guild.id)
        player = state.player
        if not player or not player.connected:
            await interaction.response.send_message("The bot is not currently in a voice channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self._send_controls(interaction.channel, interaction.guild.id)
        await interaction.followup.send("Controls panel sent.", ephemeral=True)


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Radio(bot))
