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

# Discord imports
import discord
from discord.ext import commands

# Custom imports
from utils import JsonInteracts

# Redef
read_json = JsonInteracts.read_json


class music(commands.Cog):
    """
    Musicbot functions
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot
        self.song_queue = dict()

        # Populate dict object
        for guild in self.bot.guilds:
            self.song_queue[guild.id] = []
            print(self.song_queue)

        # pafy request
        pafy.set_api_key(read_json(Path('environment.json'))['GOOGLE API'])

    # Adds a song to queue
    async def enqueue(self, ctx, song):
        # Get best audio url
        url = pafy.new(song).getbestaudio().url

        # Add to queue
        self.song_queue[ctx.guild.id].append(url)

    # Plays the queue
    async def playsong(self, ctx, song):
        # Get the queue
        song_queue = self.song_queue[ctx.guild.id]

        # Append if empty
        if len(song_queue) == 0:
            await self.enqueue(ctx, song)

        # Loop through queue
        for song in song_queue:
            # Remove from list
            song_queue.remove(song)

            # Send message playing
            await ctx.send('Now playing')

            # Play song to voice channel using FFMpeg with volum controls
            ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song)))

            # Set volume
            ctx.voice_client.source.volume = 0.5

    # Check if loaded
    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('Music Cog loaded')

    # Player
    @commands.command(
        name='play',
        brief='Plays a song from a YouTube link.',
        help='Plays a song from a YouTube link. If one is already playing, adds to the queue.'
    )
    async def play(self, ctx, song):
        # Join user channel and play, else queue
        if ctx.guild.voice_client not in self.bot.voice_clients:
            await ctx.author.voice.channel.connect()
            await self.playsong(ctx, song)
        else:
            await ctx.send(f'{song} added to queue')
            await self.enqueue(ctx, song)

    # Leave channel
    @commands.command()
    async def leave(self, ctx):
        await ctx.voice_client.disconnect()


# Add to bot
def setup(bot) -> None:
    bot.add_cog(music(bot))