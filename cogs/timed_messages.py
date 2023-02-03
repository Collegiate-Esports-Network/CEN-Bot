__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Timed Messages Functions"""

# Python imports
from datetime import datetime

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands, tasks
from discord import app_commands

# typing
from typing import Optional
from typing import Literal
from datetime import time

# Logging
import logging
from asyncpg.exceptions import PostgresError
logger = logging.getLogger('timed_messages')


class timed_messages(commands.GroupCog, name='timed_messages'):
    """These are the timed message functions.
    """
    # Init
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()

    # Add a timed message
    @app_commands.command(
        name='update',
        description="Updates or adds a timed message"
    )
    @app_commands.describe(
        content="The message you want sent",
        time_stamp="The time and timezone you want the message sent at"
    )
    @app_commands.rename(
        DoW='Day of Week'
    )
    @commands.has_role('bot mangaer')
    async def timed_mesages_update(self, interaction: discord.Interaction, job_id: int, channel: discord.TextChannel, content: str, time_stamp: time,
                                   DoW: Optional[Literal['0: Sunday', '1: Monday', '2: Tuesday', '3: Wednesday', '4: Thursday', '5: Friday', '6: Saturday']]):
        # Convert day of week to int
        if DoW is not None:
            DoW = int(DoW[0:1])

        # Add to/Update database
        if job_id is None:
            try:
                async with self.bot.pool.acquire() as con:
                    await con.execute("INSERT INTO timedmessages (guild_id, channel_id, content, time_stamp, DoW) VALUES ($1, $2, $3, $4, $5)", interaction.guild.id, channel.id, content, time_stamp, DoW)
            except PostgresError as e:
                logger.exception(e)
                await interaction.response.send_message("There was an error upserting your data, please try again.", ephemeral=True)
            except Exception as e:
                logger.exception(e)
                await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            else:
                await interaction.response.send_message("Message added.", ephemeral=False)
        else:
            try:
                async with self.bot.pool.acquire() as con:
                    await con.execute("UPDATE timedmessages SET content=$1, time_stamp=$2, DoW=$3 WHERE guild_id=$4 and job_id=$5", content, time_stamp, DoW, interaction.guild.id, job_id)
            except PostgresError as e:
                logger.exception(e)
                await interaction.response.send_message("There was an error upserting your data, please try again.", ephemeral=True)
            except Exception as e:
                logger.exception(e)
                await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            else:
                await interaction.response.send_message("Message updated.", ephemeral=False)

    # Remove a timed message
    @app_commands.command(
        name='remove',
        description="Removes a timed message"
    )
    @commands.has_role('bot manager')
    async def timed_messages_remove(self, interaction: discord.Interaction, job_id: int):
        try:
            async with self.bot.pool.acquire() as con:
                await con.execute("DELETE FROM timedmessages WHERE job_id=$1 AND guild_id=$2", job_id, interaction.guild.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error deleting your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Message deleted.", ephemeral=False)

    # Get all timed messages for this server
    @app_commands.command(
        name='get_jobs',
        description="Gets all jobs associated with this guild"
    )
    @commands.has_role('bot manager')
    async def timed_messages_get_jobs(self, interaction: discord.Interaction):
        # Get all messages
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("SELECT * FROM timedmessages WHERE guild_id=$1", interaction.guild.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message(response)

    # @tasks.loop(seconds=60, reconnect=True)
    # async def timed_messages_send(self):
    #     # Get current datetime
    #     now = datetime.now()

    #     # Get all messages sent this minute


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(timed_messages(bot))