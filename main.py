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

# Discord imports
import discord
from discord.ext.commands import Bot

# Custom imports
from utils import JsonInteracts

# Redef
read_json = JsonInteracts.Standard.read_json

# Load environment variables
TOKEN = read_json(Path('environment.json'))['TOKEN']

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
bot.version = '0.5.0'


# Verify login
@bot.event
async def on_ready():
    logging.info(f'{bot.user.name} has connected to the Discord!')


# Log logoff
@bot.event
async def on_disconnect():
    logging.info(f'{bot.user.name} has disconnected from the Discord!')


# Simple error handling
@bot.event
async def on_command_error(ctx, error):
    logging.error(f'{ctx.command.cog_name} threw an error: {error}')


# main
if __name__ == '__main__':
    bot.load_extension('cogs.utility')
    bot.load_extension('cogs.activitylog')
    bot.load_extension('cogs.rolereactions')
    bot.load_extension('cogs.music')
    bot.run(TOKEN)