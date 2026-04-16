"""Admin functions"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

# Standard library
import asyncio
from logging import getLogger

# Third-party
from discord.utils import utcnow
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
        name='sync_commands',
        description="Forces the bot to sync commands."
    )
    async def sync_commands(self, ctx: commands.Context) -> None:
        """Force a global slash command tree sync.

        :param ctx: the command context
        :type ctx: commands.Context
        """
        await self.bot.tree.sync()
        log.info("The bot commands were forcibly synced")
        await ctx.reply("The bot commands were forcibly synced.")

    @commands.is_owner()
    @commands.dm_only()
    @commands.command(
        name='sync_guilds',
        description="Reconciles the bot's current guilds with cenbot.guilds."
    )
    async def sync_guilds(self, ctx: commands.Context) -> None:
        """Reconcile ``cenbot.guilds`` with the guilds the bot currently occupies.

        Upserts all active guilds, soft-deletes any that are no longer present,
        and hard-deletes rows that have been soft-deleted for more than 90 days.

        :param ctx: the command context
        :type ctx: commands.Context
        """
        current_ids = [guild.id for guild in self.bot.guilds]

        try:
            async with self.bot.db_pool.acquire() as conn:
                # Upsert all current guilds, clearing removed_at for any that rejoined
                await conn.executemany("""
                                       INSERT INTO cenbot.guilds (id, name, joined_at)
                                       VALUES ($1, $2, $3)
                                       ON CONFLICT (id) DO UPDATE
                                       SET name = EXCLUDED.name,
                                           removed_at = NULL
                                       """, [(guild.id, guild.name, utcnow()) for guild in self.bot.guilds])
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
        name='load',
        description="Loads an available cog.",
    )
    async def load(self, ctx: commands.Context, *, cog: str) -> None:
        """Load a cog by name.

        :param ctx: the command context
        :type ctx: commands.Context
        :param cog: the module name of the cog to load (e.g. ``moderation``)
        :type cog: str
        """
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
        """Reload a currently loaded cog by name.

        :param ctx: the command context
        :type ctx: commands.Context
        :param cog: the module name of the cog to reload (e.g. ``moderation``)
        :type cog: str
        """
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
        """Unload a currently loaded cog by name.

        :param ctx: the command context
        :type ctx: commands.Context
        :param cog: the module name of the cog to unload (e.g. ``moderation``)
        :type cog: str
        """
        try:
            await self.bot.unload_extension(f'cogs.{cog}')
        except ExtensionNotLoaded as e:
            log.error(e)
            await ctx.reply(f"'{cog}' cannot be unloaded as it was never loaded.")
        else:
            log.info(f"'{cog}' was unloaded")
            await ctx.reply(f"'{cog}' was unloaded")

    async def _send_announcement(self, msg: str, delay_minutes: int, requester_id: int) -> None:
        """Sends an announcement to all guild owners, optionally after a delay.

        :param msg: the message to send
        :type msg: str
        :param delay_minutes: minutes to wait before sending
        :type delay_minutes: int
        :param requester_id: the user id to DM a completion summary to
        :type requester_id: int
        """
        if delay_minutes > 0:
            await asyncio.sleep(delay_minutes * 60)

        app_info = await self.bot.application_info()
        bot_owner_id = app_info.owner.id

        sent, failed = 0, []
        for guild in self.bot.guilds:
            if guild.owner_id == bot_owner_id:
                continue
            try:
                owner = await self.bot.fetch_user(guild.owner_id)
                await owner.send(msg)
                sent += 1
            except Exception as e:
                log.warning(f"Could not DM owner of '{guild.name}' ({guild.id}): {e}")
                failed.append(guild.name)

        requester = await self.bot.fetch_user(requester_id)
        summary = f"Announcement complete. Sent to {sent} guild owner(s)."
        if failed:
            summary += f"\nFailed: {', '.join(failed)}"
        await requester.send(summary)

    @commands.is_owner()
    @commands.dm_only()
    @commands.command(
        name='announce',
        description="Announces something to guild owners."
    )
    async def announce(self, ctx: commands.Context, delay_minutes: int = 0, *, msg: str) -> None:
        """Announces a message to all guild owners, with an optional delay.

        :param ctx: the command context
        :type ctx: commands.Context
        :param delay_minutes: minutes to wait before sending (default: 0)
        :type delay_minutes: int
        :param msg: the message to send
        :type msg: str
        """
        if delay_minutes < 0:
            await ctx.reply("Delay must be 0 or greater.")
            return

        asyncio.create_task(self._send_announcement(msg, delay_minutes, ctx.author.id))

        if delay_minutes > 0:
            await ctx.reply(f"Announcement scheduled in {delay_minutes} minute(s). You'll receive a summary when it sends.")
        else:
            await ctx.reply("Announcement sending. You'll receive a summary when complete.")


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Admin(bot))