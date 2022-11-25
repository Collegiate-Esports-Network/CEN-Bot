__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Reaction role functions"""

# Python imports
from typing import Optional

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal

# Custom imports
from helper.get_id import get_id


class react(commands.GroupCog, name='react'):
    """These are the reaction role functions
    """
    # Init
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()

    # Set reaction channel
    @app_commands.command(
        name='setchannel',
        description="Sets the reaction channel"
    )
    @commands.has_role('bot manager')
    async def react_setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        # Update react channel
        async with self.bot.pool.acquire() as con:
            await con.execute("UPDATE serverdata SET react_channel=$1 WHERE guild_id=$2", channel.id, interaction.guild.id,)

        # Respond
        await interaction.response.send_message("react channel saved", ephemeral=False)
    
    # Add reaction role
    @app_commands.command(
        name='add',
        description="Adds a reaction role"
    )
    async def react_add(self, interaction: discord.Interaction) -> None:
        # Create react add modal
        


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(react(bot))