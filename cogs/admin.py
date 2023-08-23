__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Admin functions"""

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
logger = logging.getLogger('admin')


class admin(commands.GroupCog, name='admin'):
    """These are all the admin functions of the bot.
    """
    # Init
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()

    # Shutdown bot safely
    @app_commands.command(
        name='shutdown',
        description="Safely shuts down the bot and saves all relevent data."
    )
    @commands.is_owner()
    async def admin_shutdown(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"{self.bot.user.name} is shutting down now", ephemeral=True)
        await self.bot.close()
        logger.info(f"{self.bot.user.name} has safely closed the connection to discord")

    # Force bot sync
    @app_commands.command(
        name='sync',
        description="Forces the bot to sync commands."
    )
    @commands.is_owner()
    async def admin_sync(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await self.bot.tree.sync()
        logger.info("The bot was forcibly synced")
        await interaction.followup.send("The bot was synced.", ephemeral=True)

    # load cogs
    @app_commands.command(
        name='load',
        description="Loads an available cog.",
    )
    @app_commands.describe(
        cog="The cog to be loaded."
    )
    @commands.is_owner()
    async def admin_load(self, interaction: discord.Interaction, cog: str) -> None:
        await self.bot.load_extension(f'cogs.{cog}')
        logger.info(f"'{cog}' was loaded")
        await interaction.response.send_message(f"'{cog}' was loaded.", ephemeral=True)

    # Reload cogs
    @app_commands.command(
        name='reload',
        description="Reloads an available cog.",
    )
    @app_commands.describe(
        cog="The cog to be reloaded."
    )
    @commands.is_owner()
    async def admin_reload(self, interaction: discord.Interaction, cog: str) -> None:
        await self.bot.reload_extension(f'cogs.{cog}')
        logger.info(f"'{cog}' was reloaded")
        await interaction.response.send_message(f"'{cog}' was reloaded.", ephemeral=True)

    # Unload cogs
    @app_commands.command(
        name='unload',
        description="Unloads an available cog.",
    )
    @app_commands.describe(
        cog="The cog to be unloaded."
    )
    @commands.is_owner()
    async def admin_unload(self, interaction: discord.Interaction, cog: str) -> None:
        await self.bot.unload_extension(f'cogs.{cog}')
        logger.info(f"'{cog}' was unloaded")
        await interaction.response.send_message(f"'{cog}' was unloaded", ephemeral=True)

    # Make an annoucement to server owners
    @app_commands.command(
        name='announce',
        description="Annouces something to server owners"
    )
    @app_commands.describe(
        msg="The message to be sent."
    )
    @commands.is_owner()
    async def admin_annouce(self, interaction: discord.Interaction, msg: str) -> None:
        return

# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(admin(bot))