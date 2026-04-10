"""Utility functions"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

# Standard library
import sys
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal
from logging import getLogger

# Third-party
import python_weather
import discord
from discord.ext import commands, tasks
from discord import app_commands

# Internal
from start import CENBot

log = getLogger('CENBot.utility')


@app_commands.guild_only()
class Utility(commands.Cog):
    """Simple commands for all."""
    def __init__(self, bot: CENBot) -> None:
        self.bot = bot

    @app_commands.command(
        name='ping',
        description="Replies with Pong! (and the bots ping)",
    )
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"Pong! ({round(self.bot.latency * 1000, 4)} ms)", ephemeral=True)

    @app_commands.command(
        name='about',
        description="Returns the current bot information",
    )
    async def about(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title='Bot Info', description="Here is the most up-to-date information on the bot.", color=0x2374A5)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        embed.add_field(name="Bot Version:", value=self.bot.version)
        embed.add_field(name="Python Version:", value=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        embed.add_field(name="Discord.py Version:", value=discord.__version__)
        embed.add_field(name="Written By:", value="[Justin Panchula](https://github.com/JustinPanchula)", inline=False)
        embed.add_field(name="Server Information:", value=f"This bot is in {len(self.bot.guilds)} servers watching over {len(set(self.bot.get_all_members()))-len(self.bot.guilds)} members.", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name='flip',
        description="Flips a coin"
    )
    async def flip(self, interaction: discord.Interaction) -> None:
        random.seed(round(discord.utils.utcnow().timestamp() * 1000))
        heads = random.randint(0, 1)

        if heads:
            await interaction.response.send_message(f"{interaction.user.mention} the coin is Heads.")
        else:
            await interaction.response.send_message(f"{interaction.user.mention} the coin is Tails.")

    @app_commands.command(name='utc')
    async def utc(self, interaction: discord.Interaction, style: Literal["Relative", "Fixed"],
                        year: int, month: int, day: int, hour: int, minute: int,
                        time_zone: Literal["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "UTC"]) -> None:
        """Convert a local time to a discord timestamp

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param style: the style of the timestamp
        :type style: Literal["Relative", "Fixed"]
        :param year: the year of the timestamp
        :type year: int
        :param month: the month of the timestamp
        :type month: int
        :param day: the day of the timestamp
        :type day: int
        :param hour: the hour of the timestamp
        :type hour: int
        :param minute: the minute of the timestamp
        :type minute: int
        :param time_zone: the timezone of the timestamp
        :type time_zone: Literal["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "UTC"]
        """
        try:
            user_time = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(time_zone))
        except ValueError as e:
            await interaction.response.send_message(f"{e}", ephemeral=True)
            return

        if style == "Relative":
            await interaction.response.send_message(f"Relative datetime: ``<t:{int(user_time.timestamp())}:R>``", ephemeral=True)
        elif style == "Fixed":
            await interaction.response.send_message(f"Fixed datetime: ``<t:{int(user_time.timestamp())}:F>``", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid timestamp format specified.", ephemeral=True)

    @app_commands.command(
        name='weather',
        description="Gets your local weather"
    )
    async def weather(self, interaction: discord.Interaction, city: str) -> None:
        """Gets your local weather forecast

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param city: the city to get weather for
        :type city: str
        """
        async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
            weather = await client.get(city)
        if weather:
            embed = discord.Embed(title='Weather Forecast', description="Here is your 3-day weather forecast.", color=discord.Color.greyple())
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
            embed.add_field(name="Currently",
                            value=f"{weather.temperature}°F and {weather.description}\nWind: {weather.wind_direction} @ {weather.wind_speed} mph",
                            inline=False)
            embed.add_field(name="Tomorrow",
                            value=f"{weather.daily_forecasts[0].lowest_temperature}°F - {weather.daily_forecasts[0].highest_temperature}°F | {weather.daily_forecasts[0].hourly_forecasts[4].kind}",
                            inline=False)
            embed.add_field(name=f"{weather.daily_forecasts[1].date}",
                            value=f"{weather.daily_forecasts[1].lowest_temperature}°F - {weather.daily_forecasts[1].highest_temperature}°F | {weather.daily_forecasts[1].hourly_forecasts[4].kind}",
                            inline=False)
            embed.add_field(name=f"{weather.daily_forecasts[2].date}",
                            value=f"{weather.daily_forecasts[2].lowest_temperature}°F - {weather.daily_forecasts[2].highest_temperature}°F | {weather.daily_forecasts[2].hourly_forecasts[4].kind}",
                            inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"Could not retrieve weather for ``{city}``.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def update_presence(self) -> None:
        """Updates the bot's presence every minute with the weather."""
        cities = ["New York", "Columbus", "Chicago", "Denver", "Los Angeles"]
        weather = None
        async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
            city = cities[discord.utils.utcnow().minute % 5]
            weather = await client.get(city)
            if weather:
                await self.bot.change_presence(activity=discord.CustomActivity(name=f"{city}: {weather.kind.name.capitalize() if not 'SUNNY' else 'Clear'}, {weather.feels_like}°F"))
                log.debug("Bot status updated")
            else:
                return

    def cog_load(self):
        self.update_presence.start()

    def cog_unload(self):
        self.update_presence.stop()


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Utility(bot))