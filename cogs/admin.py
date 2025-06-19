__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Admin functions"""

# Helpers
from modules.async_for import forasync

# Discord imports
from start import cenbot
from discord.ext import commands

# Logging
import logging
from discord.ext.commands import ExtensionAlreadyLoaded, ExtensionNotLoaded, ExtensionError
log = logging.getLogger('CENBot.admin')


class admin(commands.Cog, name='admin'):
    """These are all the admin functions of the bot.
    """
    def __init__(self, bot: cenbot) -> None:
        self.bot = bot

    @commands.is_owner()
    @commands.dm_only()
    @commands.command(
        name='sync',
        description="Forces the bot to sync commands."
    )
    async def sync(self, ctx: commands.Context) -> None:
        # Sync commands
        await self.bot.tree.sync()

        # Log
        log.info("The bot was forcibly synced")

        # Send response
        await ctx.reply("The bot was forcibly synced.")

    @commands.is_owner()
    @commands.dm_only()
    @commands.command(
        name='load',
        description="Loads an available cog.",
    )
    async def load(self, ctx: commands.Context, *, cog: str) -> None:
        try:
            await self.bot.load_extension(f'cogs.{cog}')
        except ExtensionAlreadyLoaded as e:
            log.error(e)
            await ctx.reply(f"'{cog}' already loaded.")
        else:
            log.info(f"'{cog}' was loaded")
            await ctx.reply(f"'{cog}' was loaded.")

    @commands.is_owner()
    @commands.dm_only()
    @commands.command(
        name='reload',
        description="Reloads an available cog.",
    )
    async def reload(self, ctx: commands.Context, *, cog: str) -> None:
        try:
            await self.bot.reload_extension(f'cogs.{cog}')
        except ExtensionError as e:
            log.error(e)
            await ctx.reply(f"'{cog}' was unable to be reloaded.")
        else:
            log.info(f"'{cog}' was reloaded")
            await ctx.reply(f"'{cog}' was reloaded.")

    @commands.is_owner()
    @commands.dm_only()
    @commands.command(
        name='unload',
        description="Unloads an available cog.",
    )
    async def unload(self, ctx: commands.Context, *, cog: str) -> None:
        try:
            await self.bot.unload_extension(f'cogs.{cog}')
        except ExtensionNotLoaded as e:
            log.error(e)
            await ctx.reply(f"'{cog}' cannot be unloaded as it was never loaded.")
        else:
            log.info(f"'{cog}' was unloaded")
            await ctx.reply(f"'{cog}' was unloaded")

    @commands.is_owner()
    @commands.dm_only()
    @commands.command(
        name='announce',
        description="Annouces something to guild owners."
    )
    async def annouce(self, ctx: commands.Context, *, msg: str) -> None:
        # For each guild, create DM with owner with the annoucement
        async for guild in forasync(self.bot.guilds):
            if not await self.bot.is_owner(guild.owner):
                channel = await guild.owner.create_dm()
                await channel.send(msg)

        await ctx.reply(f"Annoucement \"{msg}\" sent.")


# Add to bot
async def setup(bot: cenbot) -> None:
    await bot.add_cog(admin(bot))