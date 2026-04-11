"""Audio playback from YouTube via yt-dlp and PyAV"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

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
import discord
from discord.ext import commands
from discord import app_commands

# Internal
from start import CENBot

log = getLogger('CENBot.radio')

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
}


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

    @property
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
    """

    queue: deque = field(default_factory=deque)
    current: Track | None = None
    vc: discord.VoiceClient | None = None


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

    def _get_state(self, guild_id: int) -> GuildState:
        """Returns the GuildState for a guild, creating one if needed.

        :param guild_id: the guild's ID
        :type guild_id: int
        :returns: the guild's radio state
        :rtype: GuildState
        """
        if guild_id not in self._states:
            self._states[guild_id] = GuildState()
        return self._states[guild_id]

    async def _extract(self, url: str) -> dict | None:
        """Extracts stream info from a URL via yt-dlp (runs in thread executor).

        :param url: the YouTube video URL
        :type url: str
        :returns: yt-dlp info dict, or None on failure
        :rtype: dict | None
        """
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            except yt_dlp.utils.DownloadError as e:
                log.warning(f"yt-dlp extraction failed: {e}")
                return None
        if 'entries' in data:
            data = data['entries'][0]
        return data

    def _play_next(self, guild_id: int, error: Exception | None) -> None:
        """Called by discord.py after a track ends. Schedules the next track.

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

    async def _start_track(self, guild_id: int, track: Track) -> None:
        """Begins playback of a Track on the guild's voice client.

        :param guild_id: the guild's ID
        :type guild_id: int
        :param track: the track to play
        :type track: Track
        """
        state = self._get_state(guild_id)
        if not state.vc or not state.vc.is_connected():
            return
        state.current = track
        source = discord.PCMVolumeTransformer(PyAVSource(track.url))
        state.vc.play(source, after=lambda e: self._play_next(guild_id, e))

    @staticmethod
    def _fmt_duration(seconds: int) -> str:
        """Format a duration in seconds as ``H:MM:SS`` or ``M:SS``.

        :param seconds: the total duration in seconds
        :type seconds: int
        :returns: human-readable duration string
        :rtype: str
        """
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02}:{s:02}"
        return f"{m}:{s:02}"

    @app_commands.command(name='play', description="Play audio from a YouTube URL")
    @app_commands.describe(url="YouTube video URL")
    async def play(self, interaction: discord.Interaction, url: str) -> None:
        """Play audio from a YouTube URL, or queue it if something is already playing.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param url: the YouTube video URL
        :type url: str
        """
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You must be in a voice channel.", ephemeral=True)
            return

        await interaction.response.defer()

        state = self._get_state(interaction.guild.id)
        voice_channel = interaction.user.voice.channel

        if state.vc and state.vc.is_connected():
            if state.vc.channel != voice_channel:
                await state.vc.move_to(voice_channel)
        else:
            try:
                state.vc = await voice_channel.connect()
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
                f"Added to queue (position {len(state.queue)}): **{track.title}** [{self._fmt_duration(track.duration)}]"
            )
        else:
            await self._start_track(interaction.guild.id, track)
            await interaction.followup.send(
                f"Now playing: **{track.title}** [{self._fmt_duration(track.duration)}] — requested by {interaction.user.mention}"
            )

    @app_commands.command(name='stop', description="Stop playback and disconnect from voice")
    async def stop(self, interaction: discord.Interaction) -> None:
        """Stop playback, clear the queue, and disconnect.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        state = self._get_state(interaction.guild.id)
        if not state.vc or not state.vc.is_connected():
            await interaction.response.send_message("Not currently in a voice channel.", ephemeral=True)
            return
        state.queue.clear()
        state.current = None
        await state.vc.disconnect()
        state.vc = None
        await interaction.response.send_message("Stopped and disconnected.")

    @app_commands.command(name='pause', description="Pause the current track")
    async def pause(self, interaction: discord.Interaction) -> None:
        """Pause the currently playing track.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        state = self._get_state(interaction.guild.id)
        if not state.vc or not state.vc.is_playing():
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)
            return
        state.vc.pause()
        await interaction.response.send_message("Paused.")

    @app_commands.command(name='resume', description="Resume the paused track")
    async def resume(self, interaction: discord.Interaction) -> None:
        """Resume a paused track.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        state = self._get_state(interaction.guild.id)
        if not state.vc or not state.vc.is_paused():
            await interaction.response.send_message("Nothing is paused.", ephemeral=True)
            return
        state.vc.resume()
        await interaction.response.send_message("Resumed.")

    @app_commands.command(name='skip', description="Skip the current track")
    async def skip(self, interaction: discord.Interaction) -> None:
        """Skip the currently playing track and advance the queue.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        state = self._get_state(interaction.guild.id)
        if not state.vc or not (state.vc.is_playing() or state.vc.is_paused()):
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        state.vc.stop()
        await interaction.response.send_message("Skipped.")

    @app_commands.command(name='nowplaying', description="Show the current track")
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        """Display the currently playing track.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        state = self._get_state(interaction.guild.id)
        if not state.current:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        t = state.current
        embed = discord.Embed(title="Now Playing", color=0x2374A5)
        embed.add_field(
            name=t.title,
            value=f"[YouTube]({t.webpage_url}) • {self._fmt_duration(t.duration)} • {t.requester.mention}",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='queue', description="Show the current queue")
    async def queue(self, interaction: discord.Interaction) -> None:
        """Display the current track queue.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        state = self._get_state(interaction.guild.id)
        if not state.current and not state.queue:
            await interaction.response.send_message("The queue is empty.", ephemeral=True)
            return
        embed = discord.Embed(title="Queue", color=0x2374A5)
        if state.current:
            t = state.current
            embed.add_field(
                name="Now Playing",
                value=f"**{t.title}** [{self._fmt_duration(t.duration)}] — {t.requester.mention}",
                inline=False,
            )
        for i, t in enumerate(state.queue, start=1):
            embed.add_field(
                name=f"{i}. {t.title}",
                value=f"[{self._fmt_duration(t.duration)}] — {t.requester.mention}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Radio(bot))
