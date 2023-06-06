__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Timed Messages Functions"""

# Python imports
from enum import Enum

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# typing
from typing import Literal, Optional

# Logging
import logging
from asyncpg.exceptions import PostgresError
logger = logging.getLogger('timed_messages')


# Define ISO days of the week
class DayofWeek(Enum):
    Everyday = 0
    Monday = 1
    Tuesday = 2
    Wednesday = 3
    Thursday = 4
    Friday = 5
    Saturday = 6
    Sunday = 7


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
        hour="24-Hour time (UTC)"
    )
    @app_commands.rename(
        DoW='day_of_week'
    )
    @commands.has_role('bot mangaer')
    async def timed_mesages_update(self, interaction: discord.Interaction, channel: discord.TextChannel, content: str, hour: int, minute: int,
                                   DoW: Literal['0: Everyday', '1: Monday', '2: Tuesday', '3: Wednesday', '4: Thursday', '5: Friday', '6: Saturday', '7: Sunday'], job_id: Optional[int]):
        # Convert day of week to int
        DoW = int(DoW[0:1])

        # Add to/Update database
        if job_id is None:
            try:
                async with self.bot.db_pool.acquire() as con:
                    await con.execute("INSERT INTO timedmessages (guild_id, channel_id, content, time_hour, time_minute, DoW) VALUES ($1, $2, $3, $4, $5, $6)", interaction.guild.id, channel.id, content, hour, minute, DoW)
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
                async with self.bot.db_pool.acquire() as con:
                    await con.execute("UPDATE timedmessages SET channel_id=$1, content=$2, time_hour=$3, time_minute=$4, DoW=$5 WHERE guild_id=$6 AND job_id=$7", channel.id, content, hour, minute, DoW, interaction.guild.id, job_id)
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
            async with self.bot.db_pool.acquire() as con:
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
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT * FROM timedmessages WHERE guild_id=$1", interaction.guild.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            # Format response
            message = "```txt\n"
            for record in response:
                job_id = record['job_id']
                channel_id = record['channel_id']
                content = record['content']
                hour = record['time_hour']
                minute = record['time_minute']
                DoW = record['dow']

                # Formatting logic
                if DayofWeek(DoW).name == 'Everyday':
                    message += f"Job ID: {job_id} | Channel: #{self.bot.get_channel(channel_id).name} | Message: {content} | Sends at: {hour}:{minute} UTC {DayofWeek(DoW).name}\n"
                else:
                    message += f"Job ID: {job_id} | Channel: #{self.bot.get_channel(channel_id).name} | Message: {content} | Sends at: {hour}:{minute} UTC every {DayofWeek(DoW).name}\n"
            message += "```"

            await interaction.response.send_message(message, ephemeral=True)


# Add to bo0t
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(timed_messages(bot))