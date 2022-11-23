__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Welcome message functions"""

# Discord imports
import discord
from discord.ext import commands
from discord import app_commands

# Custom imports
from helper.get_id import get_id


class welcome(commands.GroupCog, name='welcome'):
    """These are the welcome message functions
    """
    # Init
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    # Sends a message on user join
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        # Get message channel
        async with self.bot.pool.acquire() as con:
            channel = await con.fetch("SELECT welcome_channel FROM serverdata WHERE guild_id=$1", member.guild.id)
        channel = channel[0]['welcome_channel']

        # Test for null
        if channel is None:
            return

        # Get welcome message
        async with self.bot.pool.acquire() as con:
            message = await con.fetch("SELECT welcome_message FROM serverdata WHERE guild_id=$1", member.guild.id)
        message = message[0]['welcome_message']

        # Edit welcome message
        message = message.replace('<new_member>', member.mention)

        # Send welcome message
        await self.bot.get_channel(channel).send(message)

    # Sets the welcome messsage channel
    @app_commands.command(
        name='setchannel',
        description="Sets the welcome channel"
    )
    @app_commands.describe(
        channel="Discord channel mention"
    )
    @commands.has_role('bot manager')
    async def welcome_setchannel(self, interaction: discord.Interaction, channel: str) -> None:
        # Update channel
        async with self.bot.pool.acquire() as con:
            await con.execute("UPDATE serverdata SET welcome_channel=$2 WHERE guild_id=$1", interaction.guild.id, get_id(channel))

        await interaction.response.send_message('Welcome channel set', ephemeral=True)

    # Sets the welcome message
    @app_commands.command(
        name='setmessage',
        description="Sets the welcome message"
    )
    @app_commands.describe(
        message="The welcome message. Use '<new_member>' to mention the member."
    )
    @commands.has_role('bot manager')
    async def welcome_setmessage(self, interaction: discord.Interaction, message: str) -> None:
        # Updates the welcome message
        async with self.bot.pool.acquire() as con:
            await con.execute("UPDATE serverdata SET welcome_message=$2 WHERE guild_id=$1", interaction.guild.id, message)

        # Respond
        await interaction.response.send_message('Welcome message saved', ephemeral=True)

    @app_commands.command(
        name='testmessage',
        description='Tests the welcome message'
    )
    @commands.has_role('bot manager')
    async def welcome_testmessage(self, interaction: discord.Interaction):
        # Get welcome channel
        async with self.bot.pool.acquire() as con:
            channel = await con.fetch("SELECT welcome_channel FROM serverdata WHERE guild_id=$1", interaction.guild.id)
        channel = channel[0]['welcome_channel']

        # Test if channel is null
        if channel is None:
            await interaction.response.send_message('ERROR: No welcome channel is set for this guild!', ephemeral=True)
            return
        else:
            # Get welcome message
            async with self.bot.pool.acquire() as con:
                message = await con.fetch("SELECT welcome_message FROM serverdata WHERE guild_id=$1", interaction.guild.id)
            message = message[0]['welcome_message']

            # Edit welcome message
            message = message.replace('<new_member>', interaction.user.mention)

            # Send welcome message
            await self.bot.get_channel(channel).send(message)

        # Respond
        await interaction.response.send_message("Test sent.", ephemeral=True)


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(welcome(bot))