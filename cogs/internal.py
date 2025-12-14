__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """CENBot internal listeners"""

# Discord imports
from start import cenbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
from logging import getLogger
log = getLogger('CENBot.internal')


@app_commands.guild_only()
class internal(commands.Cog):
    """CENBot internal listeners.
    """
    def __init__(self, bot: cenbot):
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
                                   INSERT INTO cenbot.guilds (guild_id)
                                   VALUES ($1)
                                   ON CONFLICT DO NOTHING
                                   """, guild.id)
        except Exception as e:
            log.exception(e)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """When a guild is left, remove the data from Supabase.

        :param guild: the guild left
        :type guild: discord.Guild
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   DELETE FROM cenbot.guilds
                                   WHERE guild_id=$1
                                   """, guild.id)
        except Exception as e:
            log.exception(e)

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        """When a thread is created, join it.

        :param thread: the thread created
        :type thread: discord.Thread
        """
        await thread.join()


# Add to bot
async def setup(bot: cenbot) -> None:
    await bot.add_cog(internal(bot))