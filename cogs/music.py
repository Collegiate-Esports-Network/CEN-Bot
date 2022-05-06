__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '0.1.0'
__status__ = 'Indev'
__doc__ = """Role management functions"""

# Python imports
# from time import sleep
import logging
from pathlib import Path
import pafy
# import vlc
from json_interacts import read_json

# Discord imports
from discord.ext import commands

# PLay music
# def playmusic(queue, ctx):
#     for url in self.queue:
#         # Get pafy video object
#         video = pafy.new(url)

#         # Find best audio stream
#         audioURL = video.getbestaudio().url
#         print(audioURL)

#         # VLC Audio Player
#         player = vlc.MediaPlayer(audioURL, '--verbose=-1')
#         player.play()

#         while player.is_playing():
#             sleep(1e-3)

#         self.playingmusic = False
#         return


class music(commands.Cog):
    """
    Role management functions
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot
        self.queue = []

        # pafy request
        pafy.set_api_key(read_json(Path.joinpath(Path.cwd(), 'environment.json'))['GOOGLE API'])

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

    # Add to music player queue
    @commands.command(name='play')
    async def addmusicqueue(self, ctx, song):
        """
        Plays audio from YouTube in a voice channel
        """
        # Join user channel if not already in it
        if ctx.guild.voice_client not in self.bot.voice_clients:
            await self.bot.get_command('join')(ctx)

        # Append to queue
        self.queue.append(song)

        # Leave channel
        await self.bot.get_command('leave')(ctx)


# Add to bot
def setup(bot) -> None:
    bot.add_cog(music(bot))