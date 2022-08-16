__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Main file of the CEN Discord client"""

# Python imports
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import os

# MySQL imports
import mysql.connector
from mysql.connector import errorcode

# Discord imports
import discord
from discord.ext.commands import Bot

# Custom imports
from utils import json_read

# Init logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[TimedRotatingFileHandler(filename='LOGGING.log', when='W6', interval=1, backupCount=3, encoding='UTF-8')]
)

# Init Intents
intents = discord.Intents.all()
intents.presences = True
intents.members = True
intents.message_content = True


# Create custom bot subclass
class mybot(Bot):
    def __init__(self) -> None:
        super().__init__(
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.playing, name='big brother'),
            description='The in-house developed CEN Bot',
            command_prefix='$$'
        )
 
    async def setup_hook(self) -> None:
        # Init
        found_extensions = []
        loaded_extensions = []
        failed_extensions = []

        # Scrape for extensions
        for file in os.listdir('./cogs'):
            if file.endswith('2.py'):
                found_extensions.append(f'cogs.{file[:-3]}')
        
        # Load extensions
        for extension in found_extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                failed_extensions.append(extension)
            else:
                loaded_extensions.append(extension)
        
        # Log
        logging.info(f'{loaded_extensions} loaded')
        logging.warning(f'{failed_extensions} not loaded')

    async def on_ready(self) -> None:
        logging.info(f'{self.user.display_name} has logged in')


# Init Bot
bot = mybot()


# Simple error handling
@bot.event
async def on_command_error(ctx, error):
    try:
        logging.error(f'{ctx.command.cog_name} threw an error: {error}')
    except AttributeError:
        logging.error(f'{error}')

# Init MySQL connection
USER = json_read(Path('environment.json'))['MYSQL USER']
PASS = json_read(Path('environment.json'))['MYSQL PASS']
HOST = json_read(Path('environment.json'))['MYSQL HOST']
DATABASE = json_read(Path('environment.json'))['MYSQL DATABASE']

try:
    cnx = mysql.connector.connect(user=USER, password=PASS, host=HOST, database=DATABASE)
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        logging.warning("Something is wrong with SQL user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        logging.warning("SQL Database does not exist")
    else:
        logging.error(err)


# main
if __name__ == '__main__':
    # Load environment variables
    TOKEN = json_read(Path('environment.json'))['TESTTOKEN']

    # Start bot
    bot.run(token=TOKEN, log_handler=None)