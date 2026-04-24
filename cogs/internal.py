"""CENBot internal listeners"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

# Standard library
import asyncio
import sys
import traceback
from logging import getLogger

# Third-party
import discord
from discord import app_commands
from discord.ext import commands, tasks
from asyncpg.exceptions import PostgresError
import python_weather

# Internal
from start import CENBot

log = getLogger('CENBot.internal')


class Internal(commands.Cog):
    """CENBot internal listeners."""
    def __init__(self, bot: CENBot):
        self.bot = bot

    def cog_load(self) -> None:
        """Set a global error handler for app commands and start the presence update task loop."""
        self.bot.tree.on_error = self._on_tree_error
        self.update_presence.start()

    def cog_unload(self) -> None:
        """Remove the global error handler for app commands and stop the presence update task loop."""
        try:
            del self.bot.tree.on_error
        except AttributeError:
            pass
        self.update_presence.stop()

    async def _alert_team(self, title: str, error: Exception) -> None:
        """DMs the bot owner with a formatted error traceback.

        :param title: the alert title
        :type title: str
        :param error: the exception to report
        :type error: Exception
        """
        tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        try:
            app_info = await self.bot.application_info()

            if app_info.team:
                member_list = await asyncio.gather(*[self.bot.fetch_user(m.id) for m in app_info.team.members])
            elif app_info.owner:
                member_list = [app_info.owner]

            for member in member_list:
                await member.send(f"**{title}**\n```\n{tb[:1900]}\n```")
        except Exception:
            log.exception("Failed to DM team error traceback")

    async def _on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """Global app command error handler.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param error: the error raised
        :type error: app_commands.AppCommandError
        """
        if isinstance(error, app_commands.CheckFailure):
            msg = str(error)
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        if isinstance(error, app_commands.CommandInvokeError):
            if error.original and isinstance(error.original, discord.HTTPException):
                # Swallow 408 Request Timeout errors, which can occur when a command takes too long to respond
                if error.original.status == 408 and "request timeout" in error.original.text.lower():
                    log.warning(f"Swallowed `408: Request Timeout` error in '/{interaction.command}', sent by {interaction.user} ({interaction.user.id})")
                    return

        # Parse command name for logging, default to "unknown" if not available
        cmd_name = interaction.command.name if interaction.command else "unknown"
        log.error(f"Unhandled app command error in '/{cmd_name}'", exc_info=error)

        # Alert the team with the error details
        await self._alert_team(f"Unhandled app command error in `/{cmd_name}`", error)

        # Send a generic error message to the user
        msg = "An unexpected error occurred."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Global prefix command error handler.

        :param ctx: the command context
        :type ctx: commands.Context
        :param error: the error raised
        :type error: commands.CommandError
        """
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.CheckFailure):
            await ctx.reply(str(error))
            return
        if isinstance(error, commands.UserInputError):
            await ctx.reply(f"Invalid input: {error}")
            return

        log.error(f"Unhandled command error in '!!{ctx.command}'", exc_info=error)
        await self._alert_team(f"Unhandled command error in `!!{ctx.command}`", error)
        await ctx.reply("An unexpected error occurred.")

    @commands.Cog.listener()
    async def on_error(self, event_method: str, *_) -> None:
        """Global event listener error handler.

        :param event_method: the name of the event that raised the exception
        :type event_method: str
        """
        error = sys.exc_info()[1]
        log.exception(f"Unhandled exception in '{event_method}'")
        if error:
            await self._alert_team(f"Unhandled exception in `{event_method}`", error)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """When a guild is joined, populate Supabase.

        :param guild: the guild joined.
        :type guild: discord.Guild
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.guilds (id, name)
                                   VALUES ($1, $2)
                                   ON CONFLICT (id) DO UPDATE SET removed_at=NULL
                                   """, guild.id, guild.name)
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

    @tasks.loop(minutes=1)
    async def update_presence(self) -> None:
        """Updates the bot's presence every minute with the weather."""
        cities = ["New York", "Columbus", "Chicago", "Denver", "Los Angeles"]
        async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
            # Rotate through a list of cities based on the current minute to ensure we get a variety of weather updates
            city = cities[discord.utils.utcnow().minute % 5]

            # Retrieve weather data
            weather = None
            try:
                weather = await client.get(city)
            except python_weather.errors.RequestError as e:
                log.exception(e)
                return

            # Only update presence if we successfully retrieved weather data
            if weather:
                await self.bot.change_presence(activity=discord.CustomActivity(name=f"{city}: {weather.kind.name.capitalize() if not 'SUNNY' else 'Clear'}, {weather.feels_like}°F"))
                log.debug("Bot status updated")
            else:
                return


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Internal(bot))