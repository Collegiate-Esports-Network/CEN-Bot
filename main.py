__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Main file of the CEN Discord client"""

# Python imports
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# Custom imports
from utils import JsonInteracts
from cbot import cbot

# Init logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[TimedRotatingFileHandler(filename='LOGGING.log', when='W6', interval=1, backupCount=3, encoding='UTF-8')]
)

# Init Bot
bot = cbot()

# Simple error handling
@bot.event
async def on_command_error(ctx, error):
    try:
        logging.error(f'{ctx.command.cog_name} threw an error: {error}')
    except AttributeError:
        logging.error(f'{error}')

# main
if __name__ == '__main__':
    # Load environment variables
    TOKEN = JsonInteracts.read(Path('environment.json'))['TESTTOKEN']

    # Start bot
    bot.run(token=TOKEN, log_handler=None)