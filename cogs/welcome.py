__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Welcome message functions"""

# Python imports
from pathlib import Path

# Discord imports
import discord
from discord.ext import commands
from discord import app_commands

# Custom imports
from utils import JsonInteracts, get_id


class welcome(commands.GroupCog, name='welcome'):
    """These are the welcome message functions
    """
    # Init
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.welcome_file = Path('data/welcome.json')
        self.welcome_data = JsonInteracts.read(self.welcome_file)
        self.save_timer = 10
        super().__init__()

    # Sends a message on user join
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        # Get welcome channel
        try:
            welcome_channel = self.welcome_data[str(member.guild.id)]['Channel']
        except KeyError:
            return
        else:
            welcome_channel = self.bot.get_channel(get_id(welcome_channel))

        # Get welcome message and edit
        try:
            welcome_message = self.welcome_data[str(member.guild.id)]['Message']
        except KeyError:
            welcome_message = 'Welcome to the server <new_user>!'
        else:
            welcome_message = welcome_message.replace('<new_user>', member.mention)

        # Send welcome message
        await welcome_channel.send(welcome_message)

        # Subtract 1 from timer
        self.save_timer -= 1

        # Check if save timer is up
        if self.save_timer <= 0:
            JsonInteracts.write(self.welcome_file, self.welcome_data)
            self.save_timer = 10

    # Sets the welcome messsage channel
    @app_commands.command(
        name='setchannel',
        description='Sets the welcome channel'
    )
    @app_commands.describe(
        channel='Discord channel mention'
    )
    @commands.has_role('bot manager')
    async def welcome_setchannel(self, interaction: discord.Interaction, channel: str) -> None:
        # Test is this guild exists in memory
        try:
            self.welcome_data[str(interaction.guild_id)]
        except KeyError:
            self.welcome_data[str(interaction.guild_id)] = {}

        # Test if a welcome channel is created for the server
        try:
            self.welcome_data[str(interaction.guild_id)]['Channel']
        except KeyError:
            self.welcome_data[str(interaction.guild_id)]['Channel'] = ''

        # Set channel
        self.welcome_data[str(interaction.guild_id)]['Channel'] = get_id(channel)

        await interaction.response.send_message('Welcome channel set', ephemeral=True)

    # Sets the welcome message
    @app_commands.command(
        name='setmessage',
        description='Sets the welcome message'
    )
    @app_commands.describe(
        message='The welcome message. Use "<new_user>" to mention the member.'
    )
    @commands.has_role('bot manager')
    async def welcome_setmessage(self, interaction: discord.Interaction, message: str) -> None:
        # Test is this guild exists in memory
        try:
            self.welcome_data[str(interaction.guild_id)]
        except KeyError:
            self.welcome_data[str(interaction.guild_id)] = {}

        # Test if a welcome message is created for the server
        try:
            self.welcome_data[str(interaction.guild_id)]['Message']
        except KeyError:
            self.welcome_data[str(interaction.guild_id)]['Message'] = ''

        # Set message
        self.welcome_data[str(interaction.guild_id)]['Message'] = message

        # Respond
        await interaction.response.send_message('Welcome message saved', ephemeral=True)

    @app_commands.command(
        name='testmessage',
        description='Tests the welcome message'
    )
    @commands.has_role('bot manager')
    async def welcome_testmessage(self, interaction: discord.Interaction):
        tests = {
            'Channel': None,
            'Message': None
        }

        # Test if a welcome channel is already created for the server
        try:
            self.welcome_data[str(interaction.guild_id)]['Channel']
        except KeyError:
            tests['Channel'] = False
        else:
            welcome_channel = self.bot.get_channel(self.welcome_data[str(interaction.guild_id)]['Channel'])

        # Test if a welcome message is created for the server
        try:
            self.welcome_data[str(interaction.guild_id)]['Message']
        except KeyError:
            tests['Message'] = False
        else:
            welcome_message = self.welcome_data[str(interaction.guild_id)]['Message']
            print(welcome_message)

        # Return if tests fail
        if tests['Channel'] is False:
            await interaction.response.send_message('ERROR: No welcome channel is set for this guild!', ephemeral=True)
        elif tests['Message'] is False:
            await interaction.response.send_message('ERROR: No welcome message is set for this guild! The default is currently being used.', ephemeral=True)

            welcome_message = 'Welcome to our server <new_user>!'
            welcome_message = welcome_message.replace('<new_user>', interaction.user.mention)
            await welcome_channel.send(welcome_message)
        else:
            welcome_message = welcome_message.replace('<new_user>', interaction.user.mention)
            await welcome_channel.send(welcome_message)

            await interaction.response.send_message('SUCCESS: All tests passed', ephemeral=True)

        # Save edits
        JsonInteracts.write(self.welcome_file, self.welcome_data)


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(welcome(bot))