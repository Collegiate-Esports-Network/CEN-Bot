__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Main file of the CEN Discord client"""

# Python imports
from dotenv import load_dotenv
import logging
from logging.handlers import TimedRotatingFileHandler
import os

# Discord imports
import discord

# Custom imports
from cbot import cbot

# Init environment
load_dotenv()

# Init logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[TimedRotatingFileHandler(filename="LOGGING.log", when='W6', interval=1, backupCount=3, encoding='UTF-8')]
)

# Init Bot
bot = cbot()


# Simple error handling
@bot.event
async def on_command_error(ctx, error):
    try:
        logging.error(f"{ctx.command.cog_name} threw an error: {error}")
    except AttributeError:
        logging.error(f"{error}")


# On bot join update server data
@bot.event
async def on_guild_join(guild: discord.Guild):
    async with bot.pool.acquire() as con:
        await con.execute("INSERT INTO serverdata (guild_id) VALUES ($1) ON CONFLICT DO NOTHING", guild.id)
        await con.execute("INSERT INTO xp (guild_id) VALUES ($1) ON CONFLICT DO NOTHING", guild.id)


# On bot leave, delete server data
@bot.event
async def on_guild_remove(guild: discord.Guild):
    async with bot.pool.acquire() as con:
        await con.execute("DELETE FROM serverdata WHERE guild_id=$1", guild.id)


# main
if __name__ == '__main__':
    # Load environment variables
    TOKEN = os.getenv('TESTTOKEN')

    # Start bot
    bot.run(token=TOKEN, log_handler=None)