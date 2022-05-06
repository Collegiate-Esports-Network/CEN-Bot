__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = 'Production'
__doc__ = """Utility Functions"""

# Python imports
import logging
from pathlib import Path

# Discord imports
import discord
from discord.ext import commands


# Get all available cogs
def getcogs():
    allcogs = []
    dir = Path('cogs')
    for entry in dir.iterdir():
        if entry.is_file():
            allcogs.append(entry.stem)
    return allcogs


class utility(commands.Cog):
    """
    Utility functions
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot

    # Check if loaded
    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('Utility Cog loaded')

    # Reload cogs
    @commands.command(
        name='reload',
        brief='Reloads cogs',
        help=f'Reloads one of the following cogs:\n{getcogs()}.'
    )
    @commands.has_role('Bot Manager')
    async def reload(self, ctx, cog):
        self.bot.reload_extension(f'cogs.{cog}')
        logging.info(f'{cog} was reloaded')
        await ctx.send(f'{cog} was reloaded')

    # Simple ping command
    @commands.command(
        name='ping',
        brief='Replies with Pong! (and the bots ping)',
        help='Replies with Pong! (and the bots ping)'
    )
    async def ping(self, ctx):
        await ctx.send(f'Pong! ({round(self.bot.latency * 1000, 4)} ms)')

    # Embed current bot info
    @commands.command(
        name='info',
        brief='Returns relevent bot information',
        help='Returns relevent bot information'
    )
    async def fetchbotinfo(self, ctx):
        embed = discord.Embed(title='Bot Info', description='Here is the most up-to-date information on the bot', color=0x2374a5)
        icon = discord.File('L1.png', filename='L1.png')
        embed.set_author(name='CEN Bot', icon_url='attachment://L1.png')
        embed.add_field(name="Bot Version:", value=self.bot.version)
        embed.add_field(name="Python Version:", value='3.10.4')
        embed.add_field(name="Discord.py Version:", value=discord.__version__)
        embed.add_field(name='Written By:', value='Justin Panchula and Zach Lesniewski', inline=False)
        embed.add_field(name='Server Information:', value=f'This bot is in {len(self.bot.guilds)} servers watching over {len(set(self.bot.get_all_members()))-len(self.bot.guilds)} members.', inline=False)
        embed.set_footer(text=f'Information requested by: {ctx.author.display_name}')

        await ctx.send(file=icon, embed=embed)


# Add to bot
def setup(bot) -> None:
    bot.add_cog(utility(bot))