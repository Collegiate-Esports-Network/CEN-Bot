__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Welcome message functions"""

# Discord imports
from start import cenbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
from asyncpg.exceptions import PostgresError
log = logging.getLogger('CENBot.welcome')


@app_commands.guild_only()
class welcome(commands.GroupCog, name='welcome'):
    """These are the welcome message functions.
    """
    def __init__(self, bot: cenbot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name='set_channel',
        description="Sets the welcome channel."
    )
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET welcome_channel=$2
                                   WHERE guild_id=$1
                                   """, interaction.guild.id, channel.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Welcome channel set.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name='set_message',
        description="Sets the welcome message."
    )
    @app_commands.describe(
        message="The welcome message. Use ``<new_member>`` to mention the member."
    )
    async def set_message(self, interaction: discord.Interaction, message: str) -> None:
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.welcome
                                   SET welcome_message=$2
                                   WHERE guild_id=$1
                                   """, interaction.guild.id, message)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Welcome message set.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name='test_message',
        description="Tests the welcome message."
    )
    async def test_message(self, interaction: discord.Interaction):
        # Get welcome message
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT cenbot.guilds.welcome_channel, cenbot.welcome.welcome_message
                                             FROM cenbot.guilds INNER JOIN cenbot.welcome ON (cenbot.guilds.guild_id=cenbot.welcome.guild_id)
                                             WHERE cenbot.guilds.guild_id=$1
                                             """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again later.", ephemeral=True)
            return

        # Send welcome message
        if record:
            if record['welcome_channel']:
                try:
                    await self.bot.get_channel(record['welcome_channel']).send(record['welcome_message'].replace('<new_member>', interaction.user.mention))
                except AttributeError as e:
                    log.exception(e)
                    await interaction.response.send_message("There is no welcome channel set.", ephemeral=True)
                    return
                finally:
                    # Respond
                    await interaction.response.send_message("Test sent.", ephemeral=True)

    # Sends a message on user join
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        # Get welcome channel
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT cenbot.guilds.welcome_channel, cenbot.welcome.welcome_message
                                             FROM cenbot.guilds INNER JOIN cenbot.welcome ON (cenbot.guilds.guild_id=cenbot.welcome.guild_id)
                                             WHERE cenbot.guilds.guild_id=$1
                                             """, member.guild.id)
        except PostgresError as e:
            log.exception(e)
            return

        # Send welcome message
        if record['welcome_channel']:
            try:
                await self.bot.get_channel(record['welcome_channel']).send(record['welcome_message'].replace('<new_member>', member.user.mention))
            except AttributeError as e:
                log.exception(e)


# Add to bot
async def setup(bot: cenbot) -> None:
    await bot.add_cog(welcome(bot))