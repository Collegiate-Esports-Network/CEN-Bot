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

# Discord imports
import discord
from discord.ext import commands
import pafy

# Custom imports
from utils import JsonInteracts


class music(commands.Cog):
    """These are all functions related to the music functions
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot
        self.play_queue = {}

        for guild in self.bot.guilds:
            self.play_queue[f'{guild.id}'] = []

        # pafy request
        pafy.set_api_key(JsonInteracts.Standard.read_json(Path('environment.json'))['GOOGLE API'])

    async def playsongs(self, ctx):
        queue = self.play_queue[f'{ctx.guild.id}']

        for url in queue:
            ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url)))
            ctx.voice_client.source.volume = 0.5

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
        brief='Plays the radio in your voice channel',
        help='Plays the radio in your voice channel. If the radio is already playing it adds to the queue'
    )
    async def play(self, ctx, song):
        # Get queue
        queue = self.play_queue[f'{ctx.guild.id}']

        # Get song link
        url = pafy.new(song).getbestaudio().url

        # If queue is empty add and play, else just add
        if len(queue) == 0:
            # Add to queue
            queue.append(url)

            # Play
            await self.playsongs(ctx)
        else:
            queue.append(url)
            await ctx.send('Added to queue')

    # Stop
    @commands.command(
        name='stop',
        brief='Stops the radio',
        help='Stops the radio and clears the queue'
    )
    async def stop(self, ctx):
        return


# Add to bot
def setup(bot) -> None:
    bot.add_cog(music(bot))