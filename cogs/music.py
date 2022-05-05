__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '0.1.0'
__status__ = 'Indev'
__doc__ = """Role management functions"""

# Python imports
import logging
import pafy
import vlc

# Discord imports
from discord.ext import commands


class music(commands.Cog):
    """
    Role management functions
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot
        self.queue = []

    # Check if loaded
    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('Music Cog loaded')

    # Helper functions
    @commands.command(name='join')
    async def join(self, ctx):
        """
        Bot joins user's voice channel
        """
        await ctx.author.voice.channel.connect()

    @commands.command(name='leave')
    async def leave(self, ctx):
        """
        Bot leaves user's voice channel
        """
        await ctx.voice_client.disconnect()

    # Youtube music player
    @commands.command(name='play')
    async def playmusic(self, ctx, song):
        """
        Plays audio from YouTube in a voice channel
        """
        # Append to queue
        self.queue.append(song)

        # Join user channel
        await self.bot.get_command('join')(ctx)

        video = pafy.new(song)
        media = video.getbest().url
        player = vlc.MediaPlayer(media)
        player.play()

        # At end of queue, leave
        await self.bot.get_command('leave')(ctx)


# Add to bot
def setup(bot) -> None:
    bot.add_cog(music(bot))