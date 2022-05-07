__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '0.1.0'
__status__ = 'Indev'
__doc__ = """Role management functions"""

# Python imports
from pathlib import Path
import logging
import threading

# Discord imports
import discord
from discord.ext import commands
import pafy

# Typing imports
from typing import List

# Custom imports
from utils import JsonInteracts


# Define Radio
def Radio(ctx, queue: List):
    for song in queue:
        ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song)))
        ctx.voice_client.source.volume = 0.5
        queue.remove(song)


class music(commands.Cog):
    """These are all functions related to the music bot
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot
        self.play_queue = {}
        self.radios = {}

        for guild in self.bot.guilds:
            self.play_queue[f'{guild.id}'] = []
            self.radios[f'{guild.id}'] = {
                'playing': False,
                'radio': None
            }

        # pafy request
        pafy.set_api_key(JsonInteracts.Standard.read_json(Path('environment.json'))['GOOGLE API'])

    # Check if loaded
    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('Music Cog loaded')

    # Join
    @commands.command(
        name='join',
        brief='The bot joins your voice channel',
        help='The bot joins your voice channel'
    )
    async def join(self, ctx):
        # Join user channel, else return
        if ctx.guild.voice_client not in self.bot.voice_clients:
            await ctx.author.voice.channel.connect()
        else:
            return

    # Leave
    @commands.command(
        name='leave',
        brief='The bot leaves your voice channel',
        help='The bot leaves your voice channel'
    )
    async def leave(self, ctx):
        await ctx.voice_client.disconnect()

    # Play
    @commands.command(
        name='play',
        brief='Plays a song in your voice channel',
        help='Plays a song in your voice channel. If a song is already playing it adds to the queue'
    )
    async def play(self, ctx, song):
        # Get queue
        queue = self.play_queue[f'{ctx.guild.id}']

        # Init radio
        radio = threading.Thread(name=f'{ctx.guild.id} radio', target=Radio, args=(ctx, queue))
        self.radios[f'{ctx.guild.id}']['radio'] = radio

        # Get radio dict
        radio = self.radios[f'{ctx.guild.id}']

        # If queue is empty add and play, else just add
        if len(queue) == 0:
            # Get song link
            url = pafy.new(song).getbestaudio().url

            # Add to queue
            queue.append(url)

            # Play
            radio['radio'].start()
            radio['playing'] = True

        else:
            queue.append(url)

    # Stop
    @commands.command(
        name='stop',
        brief='Stops a song in your voice channel',
        help='Stops a song in your voice channel'
    )
    async def stop(self, ctx):
        # Get radio
        radio = self.radios[f'{ctx.guild.id}']

        # Stop
        radio['radio'].join()
        radio['playing'] = False


# Add to bot
def setup(bot) -> None:
    bot.add_cog(music(bot))