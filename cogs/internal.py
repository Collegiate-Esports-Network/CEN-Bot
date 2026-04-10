"""CENBot internal listeners"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

# Standard library
from logging import getLogger

# Third-party
import discord
from discord.ext import commands
from asyncpg.exceptions import PostgresError

# Internal
from start import CENBot

log = getLogger('CENBot.internal')


class Internal(commands.Cog):
    """CENBot internal listeners."""
    def __init__(self, bot: CENBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """When a guild is joined, populate Supabase.

        :param guild: the guild joined.
        :type guild: discord.Guild
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.guilds (id)
                                   VALUES ($1)
                                   ON CONFLICT (id) DO UPDATE SET removed_at=NULL
                                   """, guild.id)
        except PostgresError as e:
            log.exception(e)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """When a guild is left, soft-delete the guild's data in Supabase.

        :param guild: the guild left
        :type guild: discord.Guild
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET removed_at=NOW()
                                   WHERE id=$1
                                   """, guild.id)
        except PostgresError as e:
            log.exception(e)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        """When a thread is created, join it.

        :param thread: the thread created
        :type thread: discord.Thread
        """
        await thread.join()


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Internal(bot))