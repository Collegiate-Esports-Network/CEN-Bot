"""Admin functions"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

# Standard library
from logging import getLogger

# Third-party
from discord.ext import commands
from discord.ext.commands import ExtensionAlreadyLoaded, ExtensionNotLoaded, ExtensionError
from asyncpg.exceptions import PostgresError

# Internal
from start import CENBot

log = getLogger('CENBot.admin')


class Admin(commands.Cog, name='admin'):
    """These are all the admin functions of the bot."""
    def __init__(self, bot: CENBot) -> None:
        self.bot = bot

    @commands.is_owner()
    @commands.dm_only()
    @commands.command(
        name='sync',
        description="Forces the bot to sync commands."
    )
    async def sync(self, ctx: commands.Context) -> None:
        await self.bot.tree.sync()
        log.info("The bot was forcibly synced")
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
        name='sync_guilds',
        description="Reconciles the bot's current guilds with cenbot.guilds."
    )
    async def sync_guilds(self, ctx: commands.Context) -> None:
        current_ids = [guild.id for guild in self.bot.guilds]

        try:
            async with self.bot.db_pool.acquire() as conn:
                # Upsert all current guilds, clearing removed_at for any that rejoined
                await conn.executemany("""
                                       INSERT INTO cenbot.guilds (id)
                                       VALUES ($1)
                                       ON CONFLICT (id) DO UPDATE SET removed_at=NULL
                                       """, [(gid,) for gid in current_ids])
                # Soft-delete guilds the bot is no longer in (if on_guild_remove failed to fire)
                soft_deleted = await conn.execute("""
                                                  UPDATE cenbot.guilds
                                                  SET removed_at=NOW()
                                                  WHERE removed_at IS NULL AND id != ALL($1)
                                                  """, current_ids)
                # Hard-delete rows soft-deleted more than 90 days ago
                hard_deleted = await conn.execute("""
                                                  DELETE FROM cenbot.guilds
                                                  WHERE removed_at IS NOT NULL
                                                    AND removed_at < NOW() - INTERVAL '90 days'
                                                  """)
        except PostgresError as e:
            log.exception(e)
            await ctx.reply("There was an error syncing guilds, please try again.")
            return

        soft_count = int(soft_deleted.split()[-1])
        hard_count = int(hard_deleted.split()[-1])
        await ctx.reply(
            f"Guild sync complete.\n"
            f"- {len(current_ids)} active guild(s) reconciled\n"
            f"- {soft_count} guild(s) marked as removed\n"
            f"- {hard_count} guild(s) purged (>90 days expired)"
        )

    @commands.is_owner()
    @commands.dm_only()
    @commands.command(
        name='announce',
        description="Announces something to guild owners."
    )
    async def announce(self, ctx: commands.Context, *, msg: str) -> None:
        # For each guild, create DM with owner with the announcement
        for guild in self.bot.guilds:
            if not await self.bot.is_owner(guild.owner):
                await guild.owner.send(msg)

        await ctx.reply(f"Announcement \"{msg}\" sent.")


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Admin(bot))