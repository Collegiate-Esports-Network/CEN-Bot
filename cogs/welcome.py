__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Welcome message functions"""

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
from asyncpg.exceptions import PostgresError
logger = logging.getLogger('welcome')


class welcome(commands.GroupCog, name='welcome'):
    """These are the welcome message functions
    """
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(
        name='setchannel',
        description="Sets the welcome channel"
    )
    @commands.has_role('bot manager')
    async def welcome_setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            async with self.bot.pool.acquire() as con:
                await con.execute("UPDATE serverdata SET welcome_channel=$2 WHERE guild_id=$1", interaction.guild.id, channel.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Welcome channel set.", ephemeral=True)

    @app_commands.command(
        name='setmessage',
        description="Sets the welcome message"
    )
    @app_commands.describe(
        message="The welcome message. Use '<new_member>' to mention the member."
    )
    @commands.has_role('bot manager')
    async def welcome_setmessage(self, interaction: discord.Interaction, message: str) -> None:
        try:
            async with self.bot.pool.acquire() as con:
                await con.execute("UPDATE serverdata SET welcome_message=$2 WHERE guild_id=$1", interaction.guild.id, message)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Welcome message set.", ephemeral=True)

    @app_commands.command(
        name='testmessage',
        description='Tests the welcome message'
    )
    @commands.has_role('bot manager')
    async def welcome_testmessage(self, interaction: discord.Interaction):
        # Get welcome message
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("SELECT welcome_channel FROM serverdata WHERE guild_id=$1", interaction.guild.id)
            channel = response[0]['welcome_channel']
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again later.", ephemeral=True)
        except AttributeError:
            await interaction.response.send_message("There is no welcome channel set", ephemeral=True)
            return

        # Get welcome message
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("SELECT welcome_message FROM serverdata WHERE guild_id=$1", interaction.guild.id)
            message = response[0]['welcome_message']
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again later.", ephemeral=True)
            return

        # Edit welcome message
        message = message.replace('<new_member>', interaction.user.mention)

        # Send welcome message
        await self.bot.get_channel(channel).send(message)

        # Respond
        await interaction.response.send_message("Test sent.", ephemeral=True)

    # Sends a message on user join
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        # Get welcome channel
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("SELECT welcome_channel FROM serverdata WHERE guild_id=$1", member.guild.id)
            channel = response[0]['welcome_channel']
        except PostgresError as e:
            logger.exception(e)
        except AttributeError:
            return

        # Get welcome message
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("SELECT welcome_message FROM serverdata WHERE guild_id=$1", member.guild.id)
        except PostgresError as e:
            logger.exception(e)
            return
        else:
            message = response[0]['welcome_message']

        # Edit welcome message
        message = message.replace('<new_member>', member.mention)

        # Send welcome message
        await self.bot.get_channel(channel).send(message)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(welcome(bot))