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
    @app_commands.command()
    async def enable(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        """Enables the welcome module and sets the channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param channel: the text channel to send welcome messages to
        :type channel: discord.TextChannel
        """
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
            await interaction.response.send_message(f"Welcome channel set to {channel.mention}.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def disable(self, interaction: discord.Interaction) -> None:
        """Disables the welcome module.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET welcome_channel=NULL
                                   WHERE guild_id=$1
                                   """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Welcome disabled.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def set_message(self, interaction: discord.Interaction, message: str) -> None:
        """Sets the welcome message.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param message: the welcome message. Use "<new_user>" where you'd like to mention the new user.
        :type message: str
        """
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
    @app_commands.command()
    async def test_message(self, interaction: discord.Interaction):
        """Tests the welcome message.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
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
                await self.bot.get_channel(record['welcome_channel']).send(record['welcome_message'].replace('<new_member>', member.mention))
            except AttributeError as e:
                log.exception(e)


# Add to bot
async def setup(bot: cenbot) -> None:
    await bot.add_cog(welcome(bot))