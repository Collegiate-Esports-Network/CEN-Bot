__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "3"
__status__ = "Production"
__doc__ = """Main file of the CEN Discord client"""

# Python imports
from dotenv import load_dotenv
import os

# Discord imports
import discord

# Logging imports
import logging
import logging.config
import logging.handlers
import yaml
from asyncpg.exceptions import PostgresError

# Custom imports
from cbot import cbot

# Load the environment
load_dotenv()

# Configure logging
logging.config.dictConfig(yaml.safe_load(open('logging.yaml', 'r').read()))
logger = logging.getLogger('CENBot')

# Init bot
bot = cbot()


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    """When the bot joins a guild, add the necessary db columns

    Args:
        guild (discord.Guild): The guild joined
    """
    try:
        async with bot.db_pool.acquire() as con:
            await con.execute("INSERT INTO serverdata (guild_id) VALUES ($1) ON CONFLICT DO NOTHING", guild.id)
            await con.execute("ALTER TABLE xp ADD COLUMN IF NOT EXISTS s_$1 INT NOT NULL DEFAULT 0", guild.id)
    except PostgresError as e:
        logger.exception(e)
    except Exception as e:
        logger.exception(e)


@bot.event
async def on_guild_remove(guild: discord.Guild):
    """Remove server data when the bot is removed from the server

    Args:
        guild (discord.Guild): The guild left
    """
    try:
        async with bot.db_pool.acquire() as con:
            await con.execute("DELETE FROM serverdata WHERE guild_id=$1", guild.id)
            await con.execute("ALTER TABLE xp DROP COLUMN s_$1", guild.id)
    except PostgresError as e:
        logger.exception(e)
    except Exception as e:
        logger.exception(e)


@bot.event
async def on_thread_create(thread: discord.Thread):
    """On thread create, join

    Args:
        thread (discord.Thread): The thread created
    """
    await thread.join()

if __name__ == '__main__':
    # Load system type
    sys_name = os.name
    logger.info(f"{sys_name} system detected")

    # Change token based on evironment
    if sys_name == 'posix':
        TOKEN = os.getenv('TOKEN')
    else:
        TOKEN = os.getenv('TESTTOKEN')

    # Start bot
    bot.run(token=TOKEN, log_handler=None)