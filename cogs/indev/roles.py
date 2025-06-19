__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Guild Role Management"""

# Discord imports
from start import cenbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
from logging import getLogger
log = getLogger('CENBot.roles')


@app_commands.guild_only()
class roles(commands.GroupCog, name="role"):
    """User role selection.
    """
    def __init__(self, bot: cenbot):
        self.bot = bot

    @app_commands.command(
        name="add_role"
    )
    async def add_role(self, interation: discord.Interaction):
        """Add a role

        :param interation: the discord interaction
        :type interation: discord.Interaction
        :param role: the role to add
        :type role: discord.Role
        """
        await interation.response.send_message()


# Add to bot
async def setup(bot: cenbot) -> None:
    await bot.add_cog(roles(bot))