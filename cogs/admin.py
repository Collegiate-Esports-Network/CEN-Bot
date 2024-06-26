__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "2"
__status__ = "Production"
__doc__ = """Admin functions"""

# Discord imports
from cbot import cbot
from discord.ext import commands

# Custom imports
from helpers.forasync import forasync

# Logging
import logging
from asyncpg import PostgresError
from discord.ext.commands import ExtensionAlreadyLoaded, ExtensionNotLoaded, ExtensionError
log = logging.getLogger('CENBot.admin')


class admin(commands.GroupCog, name='admin'):
    """These are all the admin functions of the bot.
    """
    # Init
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()

    # Force bot sync
    @commands.command(
        name='sync',
        description="Forces the bot to sync commands."
    )
    @commands.is_owner()
    @commands.dm_only()
    async def admin_sync(self, ctx: commands.Context) -> None:
        await self.bot.tree.sync()

        # Sync the xp
        async for guild in forasync(self.bot.guilds):
            try:
                async with self.bot.db_pool.acquire() as con:
                    await con.execute(f"ALTER TABLE xp ADD COLUMN IF NOT EXISTS s_{guild.id} INT NOT NULL DEFAULT 0")
            except PostgresError as e:
                log.exception(e)
                await ctx.reply("There was an error syncing the xp table, please try again.")
                return

        # Log
        log.info("The bot was forcibly synced")

        # Send response
        await ctx.reply("The bot was forcibly synced.")

    # load cogs
    @commands.command(
        name='load',
        description="Loads an available cog.",
    )
    @commands.is_owner()
    @commands.dm_only()
    async def admin_load(self, ctx: commands.Context, *, cog: str) -> None:
        try:
            await self.bot.load_extension(f'cogs.{cog}')
        except ExtensionAlreadyLoaded as e:
            log.error(e)
            await ctx.reply(f"'{cog}' already loaded.")
        else:
            log.info(f"'{cog}' was loaded")
            await ctx.reply(f"'{cog}' was loaded.")

    # Reload cogs
    @commands.command(
        name='reload',
        description="Reloads an available cog.",
    )
    @commands.is_owner()
    @commands.dm_only()
    async def admin_reload(self, ctx: commands.Context, *, cog: str) -> None:
        try:
            await self.bot.reload_extension(f'cogs.{cog}')
        except ExtensionError as e:
            log.error(e)
            await ctx.reply(f"'{cog}' was unable to be reloaded.")
        else:
            log.info(f"'{cog}' was reloaded")
            await ctx.reply(f"'{cog}' was reloaded.")

    # Unload cogs
    @commands.command(
        name='unload',
        description="Unloads an available cog.",
    )
    @commands.is_owner()
    @commands.dm_only()
    async def admin_unload(self, ctx: commands.Context, *, cog: str) -> None:
        try:
            await self.bot.unload_extension(f'cogs.{cog}')
        except ExtensionNotLoaded as e:
            log.error(e)
            await ctx.reply(f"'{cog}' cannot be unloaded as it was never loaded.")
        else:
            log.info(f"'{cog}' was unloaded")
            await ctx.reply(f"'{cog}' was unloaded")

    # Make an annoucement to server owners
    @commands.command(
        name='announce',
        description="Annouces something to server owners."
    )
    @commands.is_owner()
    @commands.dm_only()
    async def admin_annouce(self, ctx: commands.Context, *, msg: str) -> None:
        # For each guild, create DM with owner with the annoucement
        async for guild in forasync(self.bot.guilds):
            if not await self.bot.is_owner(guild.owner):
                channel = await guild.owner.create_dm()
                await channel.send(msg)

        await ctx.reply(f"Annoucement \"{msg}\" sent.")


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(admin(bot))