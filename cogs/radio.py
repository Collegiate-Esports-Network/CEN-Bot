"""Audio playback from YouTube via yt-dlp and PyAV

Change summary:
- Added configurable FFmpeg Opus encoding (constants: `USE_FFMPEG_OPUS`,
    `FFMPEG_BITRATE`, `FFMPEG_BEFORE_OPTIONS`, `FFMPEG_OPTIONS`) to control
    the outbound Opus bitrate and reduce encoding artifacts.
- `_start_track()` now prefers `discord.FFmpegOpusAudio(...)` when
    `USE_FFMPEG_OPUS` is True and falls back to the in-process `PyAVSource` on
    error.
- `VolumeModal.on_submit` now only applies live volume when the current
    `state.source` exposes a `volume` attribute to avoid AttributeErrors.

Notes:
- Using ffmpeg-produced Opus gives explicit bitrate control but bypasses the
    `PCMVolumeTransformer` for live volume adjustments. To change volume while
    using Opus you can set `USE_FFMPEG_OPUS = False` or restart the track with
    a new bitrate. Testing: edit the constants near `YDL_OPTIONS`, restart the
    bot, and use `/radio play <url>` to evaluate audio quality.
"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = ["Justin Panchula", "Claude"]
__version__ = "2.0.0"
__status__ = "Development"

# Standard library
import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from logging import getLogger

# Third-party
import av
import yt_dlp
from yt_dlp.utils import DownloadError
import discord
from discord.ext import commands, tasks
from discord import app_commands

# Internal
from start import CENBot
from utils import BRAND_COLOR, format_duration

log = getLogger('CENBot.radio')

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
}

# When True, use ffmpeg to produce an Opus stream at `FFMPEG_BITRATE`
# Pros: explicit control over encoded bitrate (can reduce artifacts)
# Cons: discord.py volume transformer won't work on Opus sources; volume
# adjustments will be stored but won't affect an in-progress Opus stream.
USE_FFMPEG_OPUS = True
FFMPEG_BITRATE = '96k'
FFMPEG_BEFORE_OPTIONS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
FFMPEG_OPTIONS = f'-vn -ar 48000 -ac 2 -b:a {FFMPEG_BITRATE}'


class PyAVSource(discord.AudioSource):
    """AudioSource that decodes audio in-process via PyAV (libav* libraries).

    Decoding runs in a background daemon thread and feeds a byte buffer.
    ``read()`` pulls 20ms PCM frames (48 kHz, stereo, signed 16-bit) from
    that buffer, which is what discord.py's voice pipeline expects.
    """

    # 48000 Hz * 2 channels * 2 bytes/sample * 0.02 s/frame
    FRAME_SIZE = 3840
    # Maximum bytes to buffer ahead (~5 seconds)
    MAX_BUFFER = FRAME_SIZE * 250

    def __init__(self, url: str) -> None:
        """Start the background decode thread for the given audio URL.

        :param url: direct audio stream URL obtained from yt-dlp
        :type url: str
        """
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._done = False
        self._error: Exception | None = None

        self._thread = threading.Thread(
            target=self._decode_worker,
            args=(url,),
            daemon=True,
            name="PyAVDecoder",
        )
        self._thread.start()

    def _decode_worker(self, url: str) -> None:
        """Opens the stream, decodes and resamples audio, fills the buffer.

        :param url: direct audio stream URL from yt-dlp
        :type url: str
        """
        container = None
        try:
            container = av.open(url, options={
                'reconnect': '1',
                'reconnect_streamed': '1',
                'reconnect_delay_max': '5',
            })
            resampler = av.AudioResampler(format='s16', layout='stereo', rate=48000)

            for frame in container.decode(audio=0):
                if self._stop.is_set():
                    break
                for rf in resampler.resample(frame):
                    data = bytes(rf.planes[0])
                    with self._lock:
                        self._buffer.extend(data)

                # Throttle: don't decode further ahead than MAX_BUFFER
                while not self._stop.is_set():
                    with self._lock:
                        buffered = len(self._buffer)
                    if buffered < self.MAX_BUFFER:
                        break
                    time.sleep(0.05)

            # Flush resampler
            if not self._stop.is_set():
                for rf in resampler.resample(None):
                    with self._lock:
                        self._buffer.extend(bytes(rf.planes[0]))

        except Exception as e:
            self._error = e
            log.error(f"PyAVSource decode error: {e}")
        finally:
            if container:
                container.close()
            self._done = True

    def read(self) -> bytes:
        """Return the next 20ms PCM frame, or b'' at end of stream.

        Blocks up to 500ms for the buffer to fill if the decoder is still
        running (handles startup latency and momentary network hiccups).

        :returns: 3840 bytes of PCM, or b'' on EOF
        :rtype: bytes
        """
        for _ in range(50):
            with self._lock:
                if len(self._buffer) >= self.FRAME_SIZE:
                    break
                if self._done:
                    break
            time.sleep(0.01)

        with self._lock:
            if len(self._buffer) < self.FRAME_SIZE:
                return b''
            chunk = bytes(self._buffer[:self.FRAME_SIZE])
            del self._buffer[:self.FRAME_SIZE]
            return chunk

    def cleanup(self) -> None:
        """Signal the decode thread to stop and release resources.

        Called automatically by discord.py when the source is no longer needed.
        """
        self._stop.set()

    def is_opus(self) -> bool:
        return False


@dataclass
class Track:
    """Metadata for a single queued audio track.

    :param title: the video title from yt-dlp
    :param url: the direct audio stream URL
    :param webpage_url: the original YouTube page URL (for display)
    :param duration: track length in seconds
    :param requester: the guild member who requested the track
    """

    title: str
    url: str
    webpage_url: str
    duration: int
    requester: discord.Member


@dataclass
class GuildState:
    """Per-guild radio playback state.

    :param queue: ordered queue of upcoming tracks
    :param current: the track currently playing, or ``None``
    :param vc: the active voice client, or ``None`` when disconnected
    :param source: the active PCMVolumeTransformer for live volume control
    :param volume: playback volume as a fraction (0.0-2.0, default 1.0)
    :param play_start: ``time.time()`` when the current track began
    :param paused_at: ``time.time()`` when playback was paused, or ``None``
    :param paused_duration: accumulated seconds spent paused for the current track
    :param controls_message: the pinned controls panel message, or ``None``
    :param controls_view: the live View attached to the controls message
    """

    queue: deque = field(default_factory=deque)
    current: Track | None = None
    vc: discord.VoiceClient | None = None
    source: discord.PCMVolumeTransformer | None = None
    volume: float = 1.0
    play_start: float | None = None
    paused_at: float | None = None
    paused_duration: float = 0.0
    controls_message: discord.Message | None = None
    controls_view: discord.ui.View | None = None


class VolumeModal(discord.ui.Modal, title='Set Volume'):
    """Modal for adjusting playback volume (0–100)."""

    volume_input = discord.ui.TextInput(
        label='Volume (0–100)',
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
        """Apply the submitted volume value to the current audio source.

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
        state.volume = vol / 100.0
        # Only set the live volume on sources that support the attribute.
        if state.source and hasattr(state.source, 'volume'):
            state.source.volume = state.volume
        await interaction.response.defer()
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
        if not state.vc or not state.vc.is_connected():
            await interaction.response.send_message("The bot is not in a voice channel.", ephemeral=True)
            return False
        if not interaction.user.voice or interaction.user.voice.channel != state.vc.channel:
            await interaction.response.send_message("You must be in the same voice channel to use these controls.", ephemeral=True)
            return False
        return True

    @discord.ui.button(emoji='⏯', style=discord.ButtonStyle.primary, row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Toggle between paused and playing, tracking elapsed pause time.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param button: the triggered button
        :type button: discord.ui.Button
        """
        state = self.cog._get_state(self.guild_id)
        if state.vc.is_playing():
            state.vc.pause()
            state.paused_at = time.time()
        elif state.vc.is_paused():
            if state.paused_at is not None:
                state.paused_duration += time.time() - state.paused_at
                state.paused_at = None
            state.vc.resume()
        await interaction.response.defer()
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
        if not state.vc or not (state.vc.is_playing() or state.vc.is_paused()):
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        state.vc.stop()
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
        state.queue.clear()
        state.current = None
        state.source = None
        state.play_start = None
        state.paused_at = None
        state.paused_duration = 0.0
        await state.vc.disconnect()
        state.vc = None
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
    """Audio playback from YouTube."""

    def __init__(self, bot: CENBot) -> None:
        """Initialise the cog and prepare an empty per-guild state registry.

        :param bot: the bot instance
        :type bot: CENBot
        """
        self.bot = bot
        self._states: dict[int, GuildState] = {}
        super().__init__()

    async def cog_load(self) -> None:
        """Start the controls ticker task loop."""
        self._controls_ticker.start()

    async def cog_unload(self) -> None:
        """Stop the controls ticker task loop."""
        self._controls_ticker.stop()

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

    def _controls_embed(self, guild_id: int) -> discord.Embed:
        """Build the radio controls embed showing track, progress, queue, and volume.

        :param guild_id: the guild's ID
        :type guild_id: int
        :returns: the controls embed
        :rtype: discord.Embed
        """
        state = self._get_state(guild_id)
        embed = discord.Embed(title="🎵 Radio Controls", color=BRAND_COLOR)

        if state.current:
            t = state.current

            # Progress bar
            if state.play_start is not None and t.duration:
                if state.paused_at is not None:
                    elapsed = state.paused_at - state.play_start - state.paused_duration
                else:
                    elapsed = time.time() - state.play_start - state.paused_duration
                elapsed = max(0.0, min(float(t.duration), elapsed))
                bar_len = 15
                filled = round(bar_len * elapsed / t.duration)
                bar = '▓' * filled + '░' * (bar_len - filled)
                progress = f"`{bar}` {format_duration(int(elapsed))} / {format_duration(t.duration)}"
            else:
                progress = format_duration(t.duration)

            status = '⏸ Paused' if state.vc and state.vc.is_paused() else '▶ Playing'
            embed.add_field(
                name=f"{status} — {t.title}",
                value=f"[YouTube]({t.webpage_url}) • Requested by {t.requester.mention}\n{progress}",
                inline=False,
            )
        else:
            embed.add_field(
                name="Nothing playing",
                value="Use `/radio play <url>` to queue a track.",
                inline=False,
            )

        # Queue
        if state.queue:
            lines = [
                f"{i}. **{t.title}** [{format_duration(t.duration)}]"
                for i, t in enumerate(state.queue, 1)
            ]
            overflow = f"\n*…and {len(state.queue) - 5} more*" if len(state.queue) > 5 else ""
            embed.add_field(
                name=f"Up Next — {len(state.queue)} track(s)",
                value='\n'.join(lines[:5]) + overflow,
                inline=False,
            )

        embed.set_footer(text=f"🔊 Volume: {int(state.volume * 100)}%")
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
            try:
                await state.controls_message.delete()
            except discord.NotFound:
                pass
            state.controls_message = None

        view = RadioControlsView(self, guild_id)
        msg = await channel.send(embed=self._controls_embed(guild_id), view=view)
        state.controls_message = msg
        state.controls_view = view

    @tasks.loop(seconds=5)
    async def _controls_ticker(self) -> None:
        """Refresh all active controls panels every 5 seconds while audio is playing.

        Only updates guilds where the bot is actively playing to avoid unnecessary
        Discord API calls while paused or idle.
        """
        for guild_id, state in list(self._states.items()):
            if state.controls_message and state.vc and state.vc.is_playing():
                await self._update_controls(guild_id)

    @_controls_ticker.before_loop
    async def _before_ticker(self) -> None:
        """Wait for the bot to be ready before starting the ticker."""
        await self.bot.wait_until_ready()

    async def _extract(self, url: str) -> dict | None:
        """Extract stream info from a URL via yt-dlp (runs in a thread executor).

        :param url: the YouTube video URL
        :type url: str
        :returns: yt-dlp info dict, or None on failure
        :rtype: dict | None
        """
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            except DownloadError as e:
                log.warning(f"yt-dlp extraction failed: {e}")
                return None
        if 'entries' in data:
            data = data['entries'][0]
        return data

    def _play_next(self, guild_id: int, error: Exception | None) -> None:
        """Called by discord.py after a track ends; schedules the next track.

        :param guild_id: the guild's ID
        :type guild_id: int
        :param error: any error from the previous track, or None
        :type error: Exception | None
        """
        if error:
            log.error(f"Playback error in guild {guild_id}: {error}")
        state = self._get_state(guild_id)
        if state.queue:
            next_track = state.queue.popleft()
            asyncio.run_coroutine_threadsafe(self._start_track(guild_id, next_track), self.bot.loop)
        else:
            state.current = None
            state.source = None
            state.play_start = None
            state.paused_at = None
            state.paused_duration = 0.0
            asyncio.run_coroutine_threadsafe(self._update_controls(guild_id), self.bot.loop)

    async def _start_track(self, guild_id: int, track: Track) -> None:
        """Begin playback of a Track on the guild's voice client.

        :param guild_id: the guild's ID
        :type guild_id: int
        :param track: the track to play
        :type track: Track
        """
        state = self._get_state(guild_id)
        if not state.vc or not state.vc.is_connected():
            return
        state.current = track
        state.play_start = time.time()
        state.paused_at = None
        state.paused_duration = 0.0
        if USE_FFMPEG_OPUS:
            before = FFMPEG_BEFORE_OPTIONS
            options = FFMPEG_OPTIONS
            try:
                source = discord.FFmpegOpusAudio(track.url, before_options=before, options=options)
                state.source = source
                state.vc.play(source, after=lambda e: self._play_next(guild_id, e))
            except Exception as e:
                # Fall back to PyAVSource if ffmpeg path fails for any reason
                log.warning(f"FFmpegOpusAudio failed, falling back to PyAVSource: {e}")
                source = discord.PCMVolumeTransformer(PyAVSource(track.url), volume=state.volume)
                state.source = source
                state.vc.play(source, after=lambda e: self._play_next(guild_id, e))
        else:
            source = discord.PCMVolumeTransformer(PyAVSource(track.url), volume=state.volume)
            state.source = source
            state.vc.play(source, after=lambda e: self._play_next(guild_id, e))
        await self._update_controls(guild_id)

    @app_commands.command(name='play', description="Add a YouTube URL to the queue")
    @app_commands.describe(url="YouTube video URL")
    async def play(self, interaction: discord.Interaction, url: str) -> None:
        """Queue a YouTube URL and start playback if nothing is currently playing.

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

        state = self._get_state(interaction.guild.id)
        voice_channel = interaction.user.voice.channel
        first_connect = False

        if state.vc and state.vc.is_connected():
            if state.vc.channel != voice_channel:
                await state.vc.move_to(voice_channel)
        else:
            try:
                state.vc = await voice_channel.connect()
                first_connect = True
            except discord.ClientException as e:
                await interaction.followup.send(f"Could not connect to voice channel: {e}", ephemeral=True)
                return

        data = await self._extract(url)
        if not data:
            await interaction.followup.send("Could not retrieve audio from that URL.", ephemeral=True)
            return

        track = Track(
            title=data.get('title', 'Unknown'),
            url=data['url'],
            webpage_url=data.get('webpage_url', url),
            duration=data.get('duration', 0),
            requester=interaction.user,
        )

        if state.vc.is_playing() or state.vc.is_paused():
            state.queue.append(track)
            await interaction.followup.send(
                f"Added to queue (position {len(state.queue)}): **{track.title}** [{format_duration(track.duration)}]",
                ephemeral=True,
            )
            await self._update_controls(interaction.guild.id)
        else:
            await self._start_track(interaction.guild.id, track)
            await interaction.followup.send(
                f"Now playing: **{track.title}** [{format_duration(track.duration)}]",
                ephemeral=True,
            )

        if first_connect:
            await self._send_controls(voice_channel, interaction.guild.id)

    @app_commands.command(name='controls', description="Show the radio controls panel in this channel")
    async def controls(self, interaction: discord.Interaction) -> None:
        """Re-summon the radio controls panel in the current channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        state = self._get_state(interaction.guild.id)
        if not state.vc or not state.vc.is_connected():
            await interaction.response.send_message("The bot is not currently in a voice channel.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self._send_controls(interaction.channel, interaction.guild.id)
        await interaction.followup.send("Controls panel sent.", ephemeral=True)


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Radio(bot))