__author__ = 'Chris Taylor'
__copyright__ = 'Copyright CEN'
__credits__ = 'Chris Taylor'
__version__ = '0.0.0'
__status__ = 'Development'
__doc__ = """Starboard functions"""

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
from asyncpg.exceptions import PostgresError
logger = logging.getLogger('starboard')


class starboard(commands.GroupCog, name='starboard'):
    """These are the starboard functions.
    """
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()
    
    # Set the starboard channel
    @app_commands.command(
        name='setchannel',
        description="Sets the Starboard channel."
    )
    @commands.has_role('bot manager')
    async def starboard_setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE serverdata SET starboard_channel=$2 WHERE guild_id=$1", interaction.guild.id, channel.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Starboard channel set.", ephemeral=False)
    
    # Set the starboard threshold
    @app_commands.command(
        name='setthreshold',
        description="Sets the Starboard threshold"
    )
    @commands.has_role('bot manager')
    async def starboard_setthreshold(self, interaction: discord.Interaction, threshold: int):
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE serverdata SET starboard_threshold=$2 WHERE guild_id=$1", interaction.guild.id, threshold)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Starboard threshold set.", ephemeral=False)

    # Add to starboard
    @commands.Cog.listener()
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
        # Parse payload
        message = discord.utils.get
        guild = payload.guild_id
        emoji = payload.emoji

        # Logic
        if emoji == '⭐':
            if message.


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(starboard(bot))