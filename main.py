__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Main file of the CEN Discord client"""

# Python imports
from dotenv import load_dotenv
from datetime import datetime
from http.client import HTTPException
import logging.config
import logging.handlers
import logging
import yaml
import os

# Postgres imports
from asyncpg.exceptions import PostgresError

# Discord imports
import discord
from discord.ext.commands import Context

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
async def on_command_error(ctx: Context, error: discord.DiscordException):
    try:
        logger.error(f"{ctx.command.cog_name} threw an error: {error}")
    except AttributeError:
        logger.error(f"{error}")


# On bot join update server data
@bot.event
async def on_guild_join(guild: discord.Guild):
    try:
        async with bot.db_pool.acquire() as con:
            await con.execute("INSERT INTO serverdata (guild_id) VALUES ($1) ON CONFLICT DO NOTHING", guild.id)
            await con.execute("ALTER TABLE xp ADD COLUMN IF NOT EXISTS s_$1 INT NOT NULL DEFAULT 0", guild.id)
    except PostgresError as e:
        logger.exception(e)
    except Exception as e:
        logger.exception(e)


# On bot leave, delete server data
@bot.event
async def on_guild_remove(guild: discord.Guild):
    try:
        async with bot.db_pool.acquire() as con:
            await con.execute("DELETE FROM serverdata WHERE guild_id=$1", guild.id)
            await con.execute(f"ALTER TABLE xp DROP COLUMN s_{guild.id}")
    except PostgresError as e:
        logger.exception(e)
    except Exception as e:
        logger.exception(e)


# On thread create, join
@bot.event
async def on_thread_create(thread: discord.Thread):
    await thread.join()

# main
if __name__ == '__main__':
    # Load environment variables
    sys_name = os.name
    logger.info(f"{sys_name} system detected")
    if sys_name == 'posix':
        TOKEN = os.getenv('TOKEN')
    else:
        TOKEN = os.getenv('TestToken')

    # Context menu message reporting (Level 1 logging)
    @bot.tree.context_menu(name='Report Message')
    async def log_reportmessage(interaction: discord.Interaction, message: discord.Message) -> None:
        # Defer response
        await interaction.response.defer(ephemeral=True)

        # Get log channel
        try:
            async with bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT report_channel FROM serverdata WHERE guild_id=$1", interaction.guild.id)
            channel = response[0]['report_channel']
        except PostgresError as e:
            logger.exception(e)
            return
        except AttributeError as e:
            logger.exception(e)
            return

        # Get log level
        try:
            async with bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT log_level FROM serverdata WHERE guild_id=$1", interaction.guild.id)
            level = response[0]['log_level']
        except PostgresError as e:
            logger.exception(e)
            return
        except AttributeError as e:
            logger.exception(e)
            return

        # Check log level
        if level < 1:
            return

        # Reported message embed
        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar)
        embed.add_field(name='Reported Message', value=f"A message sent by {message.author.mention} was reported in {message.channel.mention}", inline=False)

        # Ignore impossible message
        try:
            embed.add_field(name='Content', value=message.content, inline=False)
        except discord.errors.HTTPException as e:
            logger.exception(e)
            return
        except HTTPException as e:
            logger.exception(e)
            return
        else:
            embed.set_footer(text=f"{datetime.now().strftime('%d/%m/%y - %H:%M:%S')}")

        # Send to channel
        await bot.get_channel(channel).send(embed=embed)

        # Respond
        await interaction.followup.send("Message reported.")

    # Start bot
    bot.run(token=TOKEN, log_handler=None)