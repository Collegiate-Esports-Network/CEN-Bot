__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = 'Production'
__doc__ = """Main file of the CEN Discord Bot"""

# Python imports
import sys
import logging
from pathlib import Path

# Custom imports
from json_interacts import read_json

# Discord imports
import discord
from discord.ext.commands import Bot

# Load environment variables
TOKEN = read_json(Path.cwd().joinpath('environment.json'))['TOKEN']

# Init logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.FileHandler(filename='LOGGING.log', encoding='UTF-8'), logging.StreamHandler(sys.stdout)]
)

# Init bot
intents = discord.Intents.all()
activity = discord.Activity(type=discord.ActivityType.watching, name='for $<command>')
bot = Bot(intents=intents, activity=activity, command_prefix='$', description='This is the in-house developed CEN Bot!')
bot.version = '0.3.1'


# Verify login
@bot.event
async def on_ready():
    logging.info(f'{bot.user.name} has connected to the Discord!')


# Log logoff
@bot.event
async def on_disconnect():
    logging.info(f'{bot.user.name} has disconnected from the Discord!')


# Simple ping command
@bot.command(name='ping')
async def ping(ctx):
    """
    Replies with Pong! (and the bots ping)
    """
    await ctx.send(f'Pong! ({round(bot.latency * 1000, 4)} ms)')


# Embed current bot info
@bot.command(name='info')
async def fetchbotinfo(ctx):
    """
    Returns relevent bot information
    """
    embed = discord.Embed(title='Bot Info', description='Here is the most up-to-date information on the bot', color=0x2374a5)
    icon = discord.File('L1.png', filename='L1.png')
    embed.set_author(name='CEN Bot', icon_url='attachment://L1.png')
    embed.add_field(name="Bot Version:", value=bot.version)
    embed.add_field(name="Python Version:", value='3.10.4')
    embed.add_field(name="Discord.py Version:", value=discord.__version__)
    embed.add_field(name='Written By:', value='Justin Panchula and Zach Lesniewski', inline=False)
    embed.add_field(name='Server Information:', value=f'This bot is in {len(bot.guilds)} servers watching over {len(set(bot.get_all_members()))-len(bot.guilds)} members.', inline=False)
    embed.set_footer(text=f'Information requested by: {ctx.author.display_name}')

    await ctx.send(file=icon, embed=embed)


# Simple error handling
@bot.event
async def on_command_error(ctx, error):
    logging.error(error)


# Reload cogs
@bot.command(name='reload', hidden=True)
async def reload(ctx, cog):
    bot.reload_extension(f'cogs.{cog}')
    logging.info(f'{cog} was reloaded')
    await ctx.send(f'{cog} was reloaded')

# main
if __name__ == '__main__':
    bot.load_extension('cogs.rolereactions')
    bot.load_extension('cogs.music')
    bot.run(TOKEN)