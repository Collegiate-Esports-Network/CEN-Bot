__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Main file of the CEN Discord client"""

# Python imports
from asyncpg.exceptions import PostgresError
from dotenv import load_dotenv
import logging.config
import logging.handlers
import logging
import yaml
import os

# Discord imports
import discord

# Custom imports
from cbot import cbot

# Init environment
load_dotenv()

# Init logging
config = yaml.safe_load(open('logging.yaml', 'r').read())
logging.config.dictConfig(config)
logger = logging.getLogger('CENBot')

# Init Bot
bot = cbot()


# Simple error handling
@bot.event
async def on_command_error(ctx, error):
    try:
        logger.error(f"{ctx.command.cog_name} threw an error: {error}")
    except AttributeError:
        logger.error(f"{error}")


# On bot join update server data
@bot.event
async def on_guild_join(guild: discord.Guild):
    try:
        async with bot.pool.acquire() as con:
            await con.execute("INSERT INTO serverdata (guild_id) VALUES ($1) ON CONFLICT DO NOTHING", guild.id)
            await con.execute("INSERT INTO xp (guild_id) VALUES ($1) ON CONFLICT DO NOTHING", guild.id)
    except PostgresError as e:
        logger.exception(e)
    except Exception as e:
        logger.exception(e)


# On bot leave, delete server data
@bot.event
async def on_guild_remove(guild: discord.Guild):
    try:
        async with bot.pool.acquire() as con:
            await con.execute("DELETE FROM serverdata WHERE guild_id=$1", guild.id)
    except PostgresError as e:
        logger.exception(e)
    except Exception as e:
        logger.exception(e)


# main
if __name__ == '__main__':
    # Load environment variables
    TOKEN = os.getenv('TESTTOKEN')

    # Start bot
    bot.run(token=TOKEN, log_handler=None)