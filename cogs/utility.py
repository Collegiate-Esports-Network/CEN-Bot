"""Utility functions"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

# Standard library
import sys
import asyncio
import random
import io
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal
from logging import getLogger

# Third-party
import python_weather
import discord
from discord.ext import commands
from discord import app_commands
import qrcode
from qrcode.image.styledpil import StyledPilImage
from PIL import Image, ImageDraw


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
        """Reply with 'Pong!' and the current gateway latency in milliseconds.

        :param interaction: the Discord interaction
        :type interaction: discord.Interaction
        """
        await interaction.response.send_message(f"Pong! ({round(self.bot.latency * 1000, 4)} ms)", ephemeral=True)

    @app_commands.command(
        name='about',
        description="Returns the current bot information",
    )
    async def about(self, interaction: discord.Interaction) -> None:
        """Display an embed with bot version, library versions, and server stats.

        :param interaction: the Discord interaction
        :type interaction: discord.Interaction
        """
        embed = discord.Embed(title='Bot Info', description="Here is the most up-to-date information on the bot.", color=0x2374A5)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        embed.add_field(name="Bot Version:", value=self.bot.version)
        embed.add_field(name="Python Version:", value=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        embed.add_field(name="Discord.py Version:", value=discord.__version__)
        embed.add_field(name="Written By:", value="[Justin Panchula](https://github.com/JustinPanchula)", inline=False)
        embed.add_field(name="Server Information:", value=f"This bot is in {len(self.bot.guilds)} servers watching over {len(set(self.bot.get_all_members()))-len(self.bot.guilds)} members.", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name='help',
        description="Lists all available slash commands.",
    )
    async def help(self, interaction: discord.Interaction) -> None:
        """Lists all available slash commands.

        :param interaction: the Discord interaction
        :type interaction: discord.Interaction
        """
        embed = discord.Embed(title="Available Commands", color=0x2374A5)

        for cmd in sorted(self.bot.tree.get_commands(), key=lambda c: c.name):
            if isinstance(cmd, app_commands.Group):
                lines = [
                    f"`/{cmd.name} {sub.name}` — {sub.description}"
                    for sub in sorted(cmd.commands, key=lambda c: c.name)
                ]
                embed.add_field(name=f"/{cmd.name}", value='\n'.join(lines), inline=False)
            else:
                embed.add_field(name=f"/{cmd.name}", value=cmd.description or "No description.", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name='flip',
        description="Flips a coin"
    )
    async def flip(self, interaction: discord.Interaction) -> None:
        """Flips a coin with a spinning animation.

        :param interaction: the Discord interaction
        :type interaction: discord.Interaction
        """
        result = random.randint(0, 1)

        await interaction.response.defer()
        msg = await interaction.followup.send("🪙", wait=True)
        frames = ["🟡", "🪙"]

        for i in range(15):
            await asyncio.sleep(0.1)
            await msg.edit(content=frames[i % 2])

        await asyncio.sleep(0.1)
        side = "Heads" if result else "Tails"
        await msg.edit(content=f"{interaction.user.mention} **{side}!** {frames[result]}")

    @app_commands.command(name='utc')
    async def utc(self, interaction: discord.Interaction, style: Literal["Relative", "Fixed"],
                        year: int, month: int, day: int, hour: int, minute: int,
                        time_zone: Literal["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "UTC"]) -> None:
        """Convert a local time to a discord timestamp

        :param interaction: the Discord interaction
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

        :param interaction: the Discord interaction
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

    @app_commands.command(
        name='qrcode',
        description="Generates a QR code from the provided text."
    )
    async def qrcode(self, interaction: discord.Interaction, text: str, logo: discord.Attachment | None = None) -> None:
        """Creates a QR code from the provided text

        :param interaction: the Discord interaction
        :type interaction: discord.Interaction
        :param text: the link or text to encode in the QR code
        :type text: str
        :param logo: an optional logo to embed in the center of the QR code (must be a square image)
        :type logo: discord.Attachment | None
        """
        # Create the QR code
        qr = qrcode.QRCode(version=4, box_size=20, border=4)
        qr.add_data(text)
        qr.make(fit=True)

        # Convert to a styled PIL image
        img = qr.make_image(image_factory=StyledPilImage).convert("RGBA")

        # Add a logo if provided
        if logo:
            logo_bytes = await logo.read()
            logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
        else:
            logo = Image.open("./cogs/assets/logo.png").convert("RGBA")

        # Resize the logo to fit within the QR code (about 15% of the QR code size)
        qr_size = img.size[0]
        logo_size = int(qr_size * 0.15)
        logo = logo.resize((logo_size, logo_size))

        # Flatten logo onto white background
        background = Image.new("RGBA", (logo_size, logo_size), "white")
        logo = Image.alpha_composite(background, logo)

        # Circular mask
        mask = Image.new("L", (logo_size, logo_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, logo_size, logo_size), fill=255)

        # Apply circular mask to logo
        logo_circular = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
        logo_circular.paste(logo, mask=mask)

        # Paste the logo onto the QR code with a circular mask to create a white border around the logo
        mask2 = Image.new("L", (logo_size, logo_size), 0)
        ImageDraw.Draw(mask2).ellipse((0, 0, logo_size, logo_size), fill=255)
        final_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
        final_logo.paste(logo_circular, mask=mask2)

        # Center the logo in the QR code
        pos = ((qr_size - logo_size) // 2, (qr_size - logo_size) // 2)
        img.paste(final_logo, pos, mask=final_logo)

        # Save the image to a byte stream
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Send the QR code as a file in the response
        await interaction.response.send_message(content=f"Here is your QR code for: ``{text}``", file=discord.File(fp=buffer, filename="qrcode.png"), ephemeral=True)


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Utility(bot))