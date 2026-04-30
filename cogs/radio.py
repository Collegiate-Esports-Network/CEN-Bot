"""Audio playback from YouTube URLs via Lavalink and Wavelink."""

__author__ = ["Justin Panchula"]
__copyright__ = "Copyright CEN"
__credits__ = ["Justin Panchula", "Claude"]
__version__ = "0.6.0"
__status__ = "Development"

# Standard library
import asyncio
import contextlib
import os
from dataclasses import dataclass
from logging import getLogger
from urllib.parse import urlparse

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
    :param controls_message: the pinned controls panel message, or ``None``
    :param controls_channel: the channel the controls panel was last sent to
    :param volume: the desired volume (0-100); applied on connect and synced on every volume change
    :param repeat: whether the current track should loop on natural end
    """

    player: wavelink.Player | None = None
    controls_message: discord.Message | None = None
    controls_channel: discord.abc.MessageableChannel | None = None
    volume: int = 50
    repeat: bool = False


class VolumeModal(discord.ui.Modal, title='Set Volume'):
    """Modal for adjusting playback volume (0-100)."""

    volume_input = discord.ui.TextInput(
        label='Volume (0-100)',
        placeholder='50 is default, 100 is max volume',
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

        await interaction.response.defer()
        await self.cog._set_volume(self.guild_id, vol)


class AddTrackModal(discord.ui.Modal, title='Add Track'):
    """Modal for queuing a track by URL or search query from the controls panel."""

    query_input = discord.ui.TextInput(
        label='URL or search terms',
        placeholder='https://youtu.be/… or lofi hip hop',
        min_length=1,
        max_length=200,
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
        """Resolve the query and queue or play the first result.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        await interaction.response.defer(ephemeral=True)

        query = self.query_input.value.strip()
        results = await self.cog._resolve_query(query)
        if not results:
            await interaction.followup.send("No results found for that query.", ephemeral=True)
            return

        state = self.cog._get_state(self.guild_id)
        player = state.player

        if not player or not player.connected:
            await interaction.followup.send("The bot is no longer connected. Use `/radio play` to start a new session.", ephemeral=True)
            return

        track = results[0]
        track.extras.requester = interaction.user.id

        _, msg = await self.cog._queue_or_play(self.guild_id, track)
        await interaction.followup.send(msg, ephemeral=True)


class SearchSelect(discord.ui.Select):
    """Select menu listing up to 5 YouTube search results.

    On selection, queues the chosen track and replaces the picker with a confirmation.
    """

    def __init__(
        self,
        cog: 'Radio',
        tracks: list[wavelink.Playable],
        original_interaction: discord.Interaction,
    ) -> None:
        """Initialise with search results and the originating interaction.

        :param cog: the Radio cog instance
        :type cog: Radio
        :param tracks: up to 5 candidate tracks from the YouTube search
        :type tracks: list[wavelink.Playable]
        :param original_interaction: the interaction that triggered /radio search
        :type original_interaction: discord.Interaction
        """
        options = [
            discord.SelectOption(
                label=track.title[:100],
                description=f"{track.author or 'Unknown'} • {format_duration(track.length // 1000) if track.length else 'Live'}"[:100],
                value=str(i),
            )
            for i, track in enumerate(tracks[:5])
        ]
        super().__init__(placeholder='Choose a track…', min_values=1, max_values=1, options=options)
        self.cog = cog
        self.tracks = tracks[:5]
        self.original_interaction = original_interaction

    async def callback(self, interaction: discord.Interaction) -> None:
        """Queue the selected track and dismiss the search picker.

        :param interaction: the discord interaction triggered by the select
        :type interaction: discord.Interaction
        """
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You must be in a voice channel to queue tracks.", ephemeral=True)
            return

        await interaction.response.defer()

        track = self.tracks[int(self.values[0])]
        track.extras.requester = self.original_interaction.user.id
        guild_id = interaction.guild_id
        state = self.cog._get_state(guild_id)
        player = state.player

        if not player or not player.connected:
            await interaction.edit_original_response(content="The bot is no longer connected. Use `/radio play` to start a new session.", view=None)
            return

        _, msg = await self.cog._queue_or_play(guild_id, track)
        await interaction.edit_original_response(content=msg, view=None)


class SearchView(discord.ui.View):
    """Ephemeral view wrapping a SearchSelect for YouTube search results."""

    def __init__(
        self,
        cog: 'Radio',
        tracks: list[wavelink.Playable],
        original_interaction: discord.Interaction,
    ) -> None:
        """Initialise with search results to display in the select.

        :param cog: the Radio cog instance
        :type cog: Radio
        :param tracks: up to 5 candidate tracks
        :type tracks: list[wavelink.Playable]
        :param original_interaction: the interaction that triggered /radio search
        :type original_interaction: discord.Interaction
        """
        super().__init__(timeout=60)
        self.add_item(SearchSelect(cog, tracks, original_interaction))


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

    @discord.ui.button(emoji='⏮', style=discord.ButtonStyle.secondary, row=0)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Replay the previously played track.

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

        history = player.queue.history
        if not history or len(history) < 1:
            await interaction.response.send_message("No previous track.", ephemeral=True)
            return

        prev_track = history[-1]
        await interaction.response.defer()

        try:
            await player.play(prev_track, paused=False)
        except Exception as e:
            log.error(f"Previous track failed in guild {self.guild_id}: {e}")

        await self.cog._update_controls(self.guild_id)

    @discord.ui.button(emoji='⏯', style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Toggle between paused and playing.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param button: the triggered button
        :type button: discord.ui.Button
        """
        await interaction.response.defer()

        state = self.cog._get_state(self.guild_id)
        player = state.player

        if player and player.paused:
            await player.pause(False)
        elif player and player.playing:
            await player.pause(True)

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

        await interaction.response.defer()
        await player.skip(force=True)

    @discord.ui.button(emoji='➕', label='Add', style=discord.ButtonStyle.success, row=0)
    async def add_track(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Open the add-track modal to queue a URL or search query.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        await interaction.response.send_modal(AddTrackModal(self.cog, self.guild_id))

    @discord.ui.button(emoji='⏹', style=discord.ButtonStyle.danger, row=0)
    async def stop_playback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Stop playback, clear the queue, and disconnect the bot.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param button: the triggered button
        :type button: discord.ui.Button
        """
        if not self.cog._get_state(self.guild_id).player:
            await interaction.response.send_message("The bot is not in a voice channel.", ephemeral=True)
            return

        await interaction.response.defer()
        await self.cog._stop_player(self.guild_id)

    @discord.ui.button(emoji='🔉', style=discord.ButtonStyle.secondary, row=1)
    async def volume_down(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Decrease volume by 10.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        new_vol = max(0, self.cog._get_state(self.guild_id).volume - 10)
        await interaction.response.defer()
        await self.cog._set_volume(self.guild_id, new_vol)

    @discord.ui.button(emoji='🔊', label='Volume', style=discord.ButtonStyle.secondary, row=1)
    async def volume_modal(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Open the volume input modal.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        await interaction.response.send_modal(VolumeModal(self.cog, self.guild_id))

    @discord.ui.button(emoji='🔊', style=discord.ButtonStyle.secondary, row=1)
    async def volume_up(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """Increase volume by 10.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        new_vol = min(100, self.cog._get_state(self.guild_id).volume + 10)
        await interaction.response.defer()
        await self.cog._set_volume(self.guild_id, new_vol)

    @discord.ui.button(emoji='🔁', style=discord.ButtonStyle.secondary, row=1)
    async def repeat(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Toggle repeat mode for the current track.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param button: the triggered button
        :type button: discord.ui.Button
        """
        state = self.cog._get_state(self.guild_id)
        state.repeat = not state.repeat
        button.style = discord.ButtonStyle.success if state.repeat else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=self.cog._controls_embed(self.guild_id), view=self)


class QueuePaginatorView(discord.ui.View):
    """Paginated view for browsing the full track queue."""

    PAGE_SIZE = 10

    def __init__(self, tracks: list[wavelink.Playable], guild_name: str) -> None:
        """Initialise with the full queue snapshot.

        :param tracks: all tracks currently in the queue
        :type tracks: list[wavelink.Playable]
        :param guild_name: the guild's display name, used in the embed title
        :type guild_name: str
        """
        super().__init__(timeout=120)
        self.tracks = tracks
        self.guild_name = guild_name
        self.page = 0
        self.max_page = max(0, (len(tracks) - 1) // self.PAGE_SIZE)
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_page.disabled = self.page == 0
        self.next_page.disabled = self.page == self.max_page

    def build_embed(self) -> discord.Embed:
        """Build the embed for the current page.

        :returns: a discord embed listing the current page of queued tracks
        :rtype: discord.Embed
        """
        start = self.page * self.PAGE_SIZE
        page_tracks = self.tracks[start:start + self.PAGE_SIZE]

        lines = []
        for i, track in enumerate(page_tracks, start + 1):
            requester = getattr(track.extras, 'requester', None)
            requester_text = f"<@{requester}>" if requester else "Unknown"
            duration = format_duration(track.length // 1000) if track.length else 'Live'
            lines.append(f"{i}. **{track.title}** [{duration}] — {requester_text}")

        embed = discord.Embed(
            title=f"Queue — {self.guild_name}",
            description='\n'.join(lines) or "Empty",
            color=BRAND_COLOR,
        )
        embed.set_footer(text=f"Page {self.page + 1}/{self.max_page + 1} • {len(self.tracks)} track(s) total")
        return embed

    @discord.ui.button(label='◀', style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Go to the previous page.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param button: the triggered button
        :type button: discord.ui.Button
        """
        self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label='▶', style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Go to the next page.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param button: the triggered button
        :type button: discord.ui.Button
        """
        self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


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

    ### State helpers ###

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

    ### Node helpers ###

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

    ### Player helpers ###

    async def _resolve_query(self, query: str) -> list[wavelink.Playable] | None:
        """Fetch tracks from Lavalink for a URL or a YouTube search query.

        Uses ``urllib.parse`` to detect URLs; bare strings are searched on YouTube.

        :param query: a YouTube URL or search keywords
        :type query: str
        :returns: a list of Playable results, or None on failure/no results
        :rtype: list[wavelink.Playable] | None
        """
        parsed = urlparse(query)
        is_url = parsed.scheme in ('http', 'https') and bool(parsed.netloc)

        try:
            if is_url:
                results = await wavelink.Playable.search(query)
            else:
                results = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
        except Exception as e:
            log.warning(f"Track search failed for query {query!r}: {e}")
            return None

        if not results:
            return None
        if isinstance(results, wavelink.Playlist):
            return list(results.tracks)
        return list(results)

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
        player.inactive_timeout = 300
        state.player = player

        try:
            await player.set_volume(state.volume)
        except Exception as e:
            log.warning(f"Initial volume set failed in guild {guild_id}: {e}")

        log.info(f"Connected to voice channel '{channel.name}' in guild {guild_id}")
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

        try:
            await player.play(track, volume=state.volume, paused=False)
        except wavelink.LavalinkException as e:
            log.warning(f"Failed to start track in guild {guild_id}: {e}")
            return False

        return True

    async def _queue_or_play(self, guild_id: int, track: wavelink.Playable) -> tuple[bool, str]:
        """Queue a track or start playback if the player is idle.

        :param guild_id: the guild's ID
        :type guild_id: int
        :param track: the track to queue or begin playing
        :type track: wavelink.Playable
        :returns: (success, user-facing message)
        :rtype: tuple[bool, str]
        """
        state = self._get_state(guild_id)
        player = state.player
        duration = format_duration(track.length // 1000) if track.length else 'Live'

        if player.playing or player.paused or player.queue:
            player.queue.put(track)
            pos = len(player.queue)
            await self._update_controls(guild_id)
            return True, f"Added to queue (position {pos}): **{track.title}** [{duration}]"

        if not await self._start_track(guild_id, track):
            return False, "Failed to start playback. Please try again."
        return True, f"Now playing: **{track.title}** [{duration}]"

    async def _stop_player(self, guild_id: int) -> None:
        """Clear the queue, disconnect the player, and refresh the controls panel.

        :param guild_id: the guild's ID
        :type guild_id: int
        """
        state = self._get_state(guild_id)
        player = state.player
        if not player:
            return
        old_channel = player.channel
        player.queue.clear()
        await self._set_voice_channel_status(guild_id, old_channel, None)
        try:
            await player.disconnect()
        except Exception as e:
            log.warning(f"Disconnect failed in guild {guild_id}: {e}")
        state.player = None
        state.repeat = False
        await self._update_controls(guild_id)

    async def _set_volume(self, guild_id: int, volume: int) -> bool:
        """Apply a volume change to the guild state and active player.

        Always persists the volume in guild state and refreshes the controls panel.
        Returns False (and logs a warning) only when a connected player rejects the change.

        :param guild_id: the guild's ID
        :type guild_id: int
        :param volume: the desired volume (0-100)
        :type volume: int
        :returns: True unless a connected player failed to apply the change
        :rtype: bool
        """
        state = self._get_state(guild_id)
        state.volume = volume
        player = state.player
        if player and player.connected:
            try:
                await player.set_volume(volume)
            except Exception as e:
                log.warning(f"Volume set failed in guild {guild_id}: {e}")
                await self._update_controls(guild_id)
                return False
        await self._update_controls(guild_id)
        return True

    ### Voice checks ###

    async def _voice_check(self, interaction: discord.Interaction) -> bool:
        """Verify voice presence and send an ephemeral error if the check fails.

        Verifies (1) the user is in a voice channel and (2) if the bot is already
        connected, the user is in the same channel.

        :param interaction: the discord interaction to validate
        :type interaction: discord.Interaction
        :returns: True if the user may issue mutating commands
        :rtype: bool
        """
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You must be in a voice channel.", ephemeral=True)
            return False

        state = self._get_state(interaction.guild_id)
        player = state.player
        if player and player.connected and interaction.user.voice.channel != player.channel:
            await interaction.response.send_message(
                "You must be in the bot's voice channel to use this command.", ephemeral=True
            )
            return False

        return True

    ### Voice channel status ###

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
        current = player.current if player else None

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

    ### Controls embed + panel ###

    def _controls_embed(self, guild_id: int) -> discord.Embed:
        """Build the radio controls embed showing track, progress, queue, and volume.

        :param guild_id: the guild's ID
        :type guild_id: int
        :returns: the controls embed
        :rtype: discord.Embed
        """
        state = self._get_state(guild_id)
        player = state.player
        current = player.current if player else None
        embed = discord.Embed(title="🎵 Radio Controls", color=BRAND_COLOR)

        if current:
            if current.artwork:
                embed.set_thumbnail(url=current.artwork)

            duration_seconds = current.length // 1000 if current.length else 0
            elapsed_seconds = player.position // 1000 if player else 0
            elapsed_seconds = max(0, min(duration_seconds, elapsed_seconds)) if duration_seconds else elapsed_seconds

            if duration_seconds:
                bar_len = 15
                filled = round(bar_len * elapsed_seconds / duration_seconds)
                bar = '▓' * filled + '░' * (bar_len - filled)
                progress = f"`{bar}` {format_duration(elapsed_seconds)} / {format_duration(duration_seconds)}"
            else:
                progress = "🔴 Live stream"

            requester = getattr(current.extras, 'requester', None)
            requester_text = f"<@{requester}>" if requester else "Unknown requester"
            title_link = f"[{current.title}]({current.uri})" if current.uri else current.title
            status = '⏸ Paused' if player and player.paused else '▶ Playing'

            embed.add_field(
                name=f"{status}",
                value=f"{title_link}\nRequested by {requester_text}\n{progress}",
                inline=False,
            )
        else:
            embed.add_field(
                name="Nothing playing",
                value="Use `/radio play <url or search>` to queue a track.",
                inline=False,
            )

        if player and player.queue:
            lines = []
            for i, track in enumerate(player.queue, 1):
                if i > 5:
                    break
                req = getattr(track.extras, 'requester', None)
                req_text = f"<@{req}>" if req else "Unknown"
                duration = format_duration(track.length // 1000) if track.length else 'Live'
                lines.append(f"{i}. **{track.title}** [{duration}] — {req_text}")
            overflow = f"\n*…and {len(player.queue) - 5} more*" if len(player.queue) > 5 else ""
            embed.add_field(
                name=f"Up Next — {len(player.queue)} track(s)",
                value='\n'.join(lines) + overflow,
                inline=False,
            )

        repeat_indicator = " • 🔁 Repeat" if state.repeat else ""
        embed.set_footer(text=f"🔊 Volume: {state.volume}/100{repeat_indicator}")
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

        state.controls_channel = channel
        msg = await channel.send(embed=self._controls_embed(guild_id), view=RadioControlsView(self, guild_id))
        state.controls_message = msg

    ### Background task ###

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

    ### Wavelink events ###

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

        # Wavelink inherits player.paused when auto-advancing the queue; always reset it
        # so that tracks started via autoplay or skip-while-paused actually play.
        if player.paused:
            with contextlib.suppress(Exception):
                await player.pause(False)

        state = self._get_state(player.guild.id)
        state.player = player
        log.info(f"Track started in guild {player.guild.id}: {(payload.original or payload.track).title!r}")
        await self._sync_voice_channel_status(player.guild.id)
        await self._update_controls(player.guild.id)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        """Refresh UI state when a track ends.

        Queue advancement is handled automatically by ``AutoPlayMode.partial``.

        :param payload: the Wavelink track-end payload
        :type payload: wavelink.TrackEndEventPayload
        """
        player = payload.player
        if not player or not player.guild:
            return

        guild_id = player.guild.id
        log.info(f"Track ended in guild {guild_id}: reason={payload.reason!r}")

        state = self._get_state(guild_id)
        if state.repeat and payload.reason == wavelink.TrackEndReason.finished:
            await self._start_track(guild_id, payload.track)
            return

        await self._sync_voice_channel_status(guild_id)
        await self._update_controls(guild_id)

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload) -> None:
        """Log track exceptions and notify the controls channel.

        :param payload: the Wavelink track-exception payload
        :type payload: wavelink.TrackExceptionEventPayload
        """
        player = payload.player
        if not player or not player.guild:
            return

        log.error(f"Playback exception in guild {player.guild.id}: {payload.exception}")
        state = self._get_state(player.guild.id)
        if state.controls_channel:
            try:
                await state.controls_channel.send("A track failed to play and was skipped.", delete_after=10)
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, payload: wavelink.TrackStuckEventPayload) -> None:
        """Log stuck tracks and force-skip them.

        :param payload: the Wavelink track-stuck payload
        :type payload: wavelink.TrackStuckEventPayload
        """
        player = payload.player
        if not player or not player.guild:
            return

        log.warning(f"Track stuck in guild {player.guild.id}: threshold={payload.threshold}ms — force-skipping")
        try:
            await player.skip(force=True)
        except Exception as e:
            log.error(f"Failed to skip stuck track in guild {player.guild.id}: {e}")

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player) -> None:
        """Disconnect and clean up state when the player has been idle too long.

        :param player: the idle Wavelink player
        :type player: wavelink.Player
        """
        if not player.guild:
            return

        guild_id = player.guild.id
        log.info(f"Inactive player in guild {guild_id} — disconnecting")
        state = self._get_state(guild_id)

        with contextlib.suppress(Exception):
            await self._set_voice_channel_status(guild_id, player.channel, None)

        try:
            await player.disconnect()
        except Exception as e:
            log.warning(f"Disconnect on inactive player failed in guild {guild_id}: {e}")

        state.player = None
        await self._update_controls(guild_id)

        if state.controls_channel:
            try:
                await state.controls_channel.send("Disconnected due to inactivity.", delete_after=15)
            except discord.HTTPException:
                pass

    ### Slash commands ###

    @app_commands.command(name='play', description="Play a YouTube URL or search query")
    @app_commands.describe(query="YouTube URL or search terms")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        """Queue a YouTube URL or search result and start playback if idle.

        Connects to the user's voice channel if the bot is not already there,
        and sends the controls panel on first connect.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param query: a YouTube URL or search keywords
        :type query: str
        """
        if not await self._voice_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        if not await self._ensure_node():
            await interaction.followup.send(self._node_unavailable_message(), ephemeral=True)
            return

        guild_id = interaction.guild_id
        voice_channel = interaction.user.voice.channel
        state = self._get_state(guild_id)
        first_connect = state.player is None or not state.player.connected

        player = await self._ensure_player(guild_id, voice_channel)
        if not player:
            await interaction.followup.send("Could not connect to the voice channel.", ephemeral=True)
            return

        results = await self._resolve_query(query)
        if not results:
            await interaction.followup.send("No results found for that query.", ephemeral=True)
            return

        track = results[0]
        track.extras.requester = interaction.user.id

        ok, msg = await self._queue_or_play(guild_id, track)
        await interaction.followup.send(msg, ephemeral=True)
        if not ok:
            return

        if first_connect:
            await self._send_controls(voice_channel, guild_id)

    @app_commands.command(name='search', description="Search YouTube and pick a track from results")
    @app_commands.describe(query="Search terms")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        """Search YouTube and present up to 5 results as a selection menu.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param query: YouTube search keywords
        :type query: str
        """
        if not await self._voice_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        if not await self._ensure_node():
            await interaction.followup.send(self._node_unavailable_message(), ephemeral=True)
            return

        guild_id = interaction.guild_id
        voice_channel = interaction.user.voice.channel
        state = self._get_state(guild_id)
        first_connect = state.player is None or not state.player.connected

        player = await self._ensure_player(guild_id, voice_channel)
        if not player:
            await interaction.followup.send("Could not connect to the voice channel.", ephemeral=True)
            return

        try:
            results = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
        except Exception as e:
            log.warning(f"Search failed for query {query!r}: {e}")
            await interaction.followup.send("Search failed. Please try again.", ephemeral=True)
            return

        if not results:
            await interaction.followup.send("No results found.", ephemeral=True)
            return

        tracks = list(results)[:5]

        if first_connect:
            await self._send_controls(voice_channel, guild_id)

        await interaction.followup.send(
            "Select a track to queue:",
            view=SearchView(self, tracks, interaction),
            ephemeral=True,
        )

    @app_commands.command(name='pause', description="Pause playback")
    async def pause(self, interaction: discord.Interaction) -> None:
        """Pause the currently playing track.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        if not await self._voice_check(interaction):
            return

        state = self._get_state(interaction.guild_id)
        player = state.player

        if not player or not player.playing:
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await player.pause(True)
        await self._sync_voice_channel_status(interaction.guild_id)
        await self._update_controls(interaction.guild_id)
        await interaction.followup.send("Paused.", ephemeral=True)

    @app_commands.command(name='resume', description="Resume paused playback")
    async def resume(self, interaction: discord.Interaction) -> None:
        """Resume a paused track.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        if not await self._voice_check(interaction):
            return

        state = self._get_state(interaction.guild_id)
        player = state.player

        if not player or not player.paused:
            await interaction.response.send_message("Playback is not paused.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await player.pause(False)
        await self._sync_voice_channel_status(interaction.guild_id)
        await self._update_controls(interaction.guild_id)
        await interaction.followup.send("Resumed.", ephemeral=True)

    @app_commands.command(name='skip', description="Skip the current track")
    async def skip(self, interaction: discord.Interaction) -> None:
        """Skip the current track and advance the queue.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        if not await self._voice_check(interaction):
            return

        state = self._get_state(interaction.guild_id)
        player = state.player

        if not player or not (player.playing or player.paused):
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            await player.skip(force=True)
        except Exception as e:
            log.warning(f"Skip failed in guild {interaction.guild_id}: {e}")
            await interaction.followup.send("Failed to skip the track.", ephemeral=True)
            return

        await interaction.followup.send("Skipped.", ephemeral=True)

    @app_commands.command(name='stop', description="Stop playback and disconnect")
    async def stop(self, interaction: discord.Interaction) -> None:
        """Stop playback, clear the queue, and disconnect from the voice channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        if not await self._voice_check(interaction):
            return

        state = self._get_state(interaction.guild_id)
        player = state.player

        if not player or not player.connected:
            await interaction.response.send_message("The bot is not in a voice channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await self._stop_player(interaction.guild_id)
        await interaction.followup.send("Stopped and disconnected.", ephemeral=True)

    @app_commands.command(name='volume', description="Set the playback volume (0-100)")
    @app_commands.describe(level="Volume level from 0 to 100")
    async def volume(self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 100]) -> None:
        """Set the playback volume.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param level: the desired volume (0-100)
        :type level: int
        """
        if not await self._voice_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        if not await self._set_volume(interaction.guild_id, level):
            await interaction.followup.send("Failed to update volume.", ephemeral=True)
            return

        await interaction.followup.send(f"Volume set to {level}/100.", ephemeral=True)

    @app_commands.command(name='remove', description="Remove a track from the queue by position")
    @app_commands.describe(position="1-based position in the queue")
    async def remove(self, interaction: discord.Interaction, position: app_commands.Range[int, 1]) -> None:
        """Remove a queued track by its 1-based position.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param position: the 1-based queue position to remove
        :type position: int
        """
        if not await self._voice_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        state = self._get_state(interaction.guild_id)
        player = state.player

        if not player or not player.queue:
            await interaction.followup.send("The queue is empty.", ephemeral=True)
            return

        idx = position - 1
        if idx >= len(player.queue):
            await interaction.followup.send(
                f"Position {position} is out of range. The queue has {len(player.queue)} track(s).",
                ephemeral=True,
            )
            return

        removed = player.queue[idx]
        del player.queue[idx]
        await self._update_controls(interaction.guild_id)
        await interaction.followup.send(
            f"Removed **{removed.title}** from position {position}.",
            ephemeral=True,
        )

    @app_commands.command(name='controls', description="Resend the radio controls panel in this channel")
    async def controls(self, interaction: discord.Interaction) -> None:
        """Re-summon the radio controls panel in the current text channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        if not await self._voice_check(interaction):
            return

        state = self._get_state(interaction.guild_id)
        player = state.player

        if not player or not player.connected:
            await interaction.response.send_message("The bot is not currently in a voice channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await self._send_controls(interaction.channel, interaction.guild_id)
        await interaction.followup.send("Controls panel sent.", ephemeral=True)

    @app_commands.command(name='nowplaying', description="Show the currently playing track")
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        """Display the currently playing track with a progress bar.

        Available to all guild members regardless of voice channel state.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        state = self._get_state(interaction.guild_id)
        player = state.player
        current = player.current if player else None

        if not current:
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)
            return

        duration_seconds = current.length // 1000 if current.length else 0
        elapsed_seconds = player.position // 1000 if player else 0
        elapsed_seconds = max(0, min(duration_seconds, elapsed_seconds)) if duration_seconds else elapsed_seconds

        if duration_seconds:
            bar_len = 15
            filled = round(bar_len * elapsed_seconds / duration_seconds)
            bar = '▓' * filled + '░' * (bar_len - filled)
            progress = f"`{bar}` {format_duration(elapsed_seconds)} / {format_duration(duration_seconds)}"
        else:
            progress = "🔴 Live stream"

        requester = getattr(current.extras, 'requester', None)
        requester_text = f"<@{requester}>" if requester else "Unknown"
        title_link = f"[{current.title}]({current.uri})" if current.uri else current.title
        status = '⏸ Paused' if player and player.paused else '▶ Playing'

        embed = discord.Embed(title="Now Playing", color=BRAND_COLOR)
        embed.description = f"{status} — {title_link}\nRequested by {requester_text}\n{progress}"
        if current.artwork:
            embed.set_thumbnail(url=current.artwork)
        embed.set_footer(text=f"🔊 Volume: {state.volume}/100")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='queue', description="Show the track queue")
    async def queue(self, interaction: discord.Interaction) -> None:
        """Display the full track queue with pagination.

        Available to all guild members regardless of voice channel state.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        state = self._get_state(interaction.guild_id)
        player = state.player

        if not player or not player.queue:
            await interaction.response.send_message("The queue is empty.", ephemeral=True)
            return

        tracks = list(player.queue)
        view = QueuePaginatorView(tracks, interaction.guild.name)
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Radio(bot))
