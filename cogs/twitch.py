__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '1.1.0'
__status__ = 'Production'
__doc__ = """Uses Twitch's API to pull live feeds from Twitch"""

# Python imports
import aiohttp
import os
from datetime import datetime

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands, tasks
from discord import app_commands

# Custom imports
from helpers.forasync import forasync

# Logging
import logging
from asyncpg.exceptions import PostgresError
log = logging.getLogger('CENBot.twitch')


@app_commands.guild_only()
class twitch(commands.GroupCog, name='twitch'):
    """These are all the Twitch function.
    """
    def __init__(self, bot: cbot):
        self.bot = bot
        super().__init__()

    def cog_load(self):
        self.check_twitch.start()

    def cog_unload(self):
        self.check_twitch.stop()

    # Set Twitch annoucement channel
    @app_commands.command(
        name='setnewschannel',
        description="Sets the channel Twitch annoucements will be sent to."
    )
    @commands.has_role('bot manager')
    async def youtube_setnewschannel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE guild_data SET twitch_news_channel=$2 WHERE guild_id=$1", interaction.guild.id, channel.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Twitch announcement channel set.", ephemeral=False)

    # Check Twitch every 1m
    @tasks.loop(minutes=1)
    async def check_twitch(self):
        # Annouce run
        log.info("Checking Twitch for new livestreams...")

        # Get all available Twitch channels
        try:
            async with self.bot.db_pool.acquire() as con:
                record = await con.fetch("SELECT * FROM twitch_channels")
        except PostgresError as e:
            log.exception(e)
            return

        # Avoid null dataset
        if record is None:
            log.info("No Twitch channels to check")
            return

        # Get and send latest uploads for each guild
        async for rec in forasync(record):

            # Annouce completion
            log.info("Finished checking Twitch channels for livestreams")


async def setup(bot: cbot) -> None:
    await bot.add_cog(twitch(bot))