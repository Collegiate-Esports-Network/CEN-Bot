__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Uses YouTube"s API to pull uploads from YouTube"""

# Helpers
from modules.async_for import forasync

# Python imports
import os
import aiohttp
from datetime import datetime

# Discord imports
from start import cenbot
import discord
from discord.ext import commands, tasks
from discord import app_commands

# Logging
from asyncpg.exceptions import PostgresError
from logging import getLogger
log = getLogger('CENBot.youtube')


@app_commands.guild_only()
class youtube(commands.GroupCog, name="youtube"):
    """YouTube operations.
    """
    def __init__(self, bot: cenbot):
        self.bot = bot
        self.base_url = "https://youtube.googleapis.com/youtube/v3/"
        self.api_key = os.getenv("YOUTUBE_KEY")

    def cog_load(self):
        self.check_youtube.start()

    def cog_unload(self):
        self.check_youtube.stop()

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name="set_channel"
    )
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Sets the channel to send YouTube alerts to.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param channel: the channel to send YouTube alerts to
        :type channel: discord.TextChannel
        """
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("""
                                  UPDATE cenbot.guilds
                                  SET youtube_alert_channel=$1
                                  WHERE guild_id=$2
                                  """, channel.id, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message(f"YouTube alert channel set to {channel.mention}.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name="add_alert"
    )
    async def add_alert(self, interaction: discord.Interaction, channel_handle: str):
        """Subscribes a guild to a YouTube channel alert.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param channel_handle: the YouTube channel handle to subscribe to (@<channel_name>)
        :type channel: discord.TextChannel
        """
        # Defer response
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Validate
        if '@' not in channel_handle:
            await interaction.followup.send("Invalid form, YouTube handle must include ``@``. Please try again.")
            return

        # Get YouTube channel information
        try:
            async with aiohttp.ClientSession() as session:
                params = {'key': self.api_key, 'part': "Id, contentDetails", 'forHandle': channel_handle}
                async with session.get(self.base_url + "channels", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        channel_id = data['items'][0]['id']
                        upload_playlist_id = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                    else:
                        log.error(f"YouTube query {response.url} returned {response.status}: {data['error']['errors'][0]['reason']}")
                        await interaction.followup.send("There was an error with the YouTube API, please try again.")
        except aiohttp.ClientError as e:
            log.exception(e)
            interaction.followup.send("There was an error with retieving the channel, please try again.")

        # Update YouTube data
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.youtube (channel_id, upload_playlist_id)
                                   VALUES ($1, $2)
                                   ON CONFLICT DO NOTHING
                                   """, channel_id, upload_playlist_id)
                await conn.execute("""
                                   UPDATE cenbot.youtube
                                   SET subscribed_guilds=ARRAY_APPEND(subscribed_guilds, $1)
                                   WHERE channel_id=$2
                                   """, interaction.guild.id, channel_id)
        except Exception as e:
            log.exception(e)
            await interaction.followup.send(f"There was an error adding ``{channel_handle}`` to your subscriptions, please try again.")
        else:
            await interaction.followup.send(f"``{channel_handle}`` has been added to your subscriptions.")

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name="remove_alert"
    )
    async def remove_alert(self, interaction: discord.Interaction, channel_handle: str):
        """Removes a guild from a YouTube channel alert.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param channel_handle: the YouTube channel handle to unsubscribe to (@<channel_name>)
        :type channel: discord.TextChannel
        """
        # Defer response
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Validate
        if '@' not in channel_handle:
            await interaction.followup.send("Invalid form, YouTube handle must include ``@``. Please try again.")
            return

        # Get YouTube channel information
        try:
            async with aiohttp.ClientSession() as session:
                params = {'key': self.api_key, 'part': "Id", 'forHandle': channel_handle}
                async with session.get(self.base_url + "channels", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        channel_id = data['items'][0]['id']
                    else:
                        log.error(f"YouTube query {response.url} returned {response.status}: {data['error']['errors'][0]['reason']}")
                        await interaction.followup.send("There was an error with the YouTube API, please try again.")
        except aiohttp.ClientError as e:
            log.exception(e)
            interaction.followup.send("There was an error with retieving the channel, please try again.")

        # Update YouTube data
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.youtube
                                   SET subscribed_guilds=ARRAY_REMOVE(subscribed_guilds, $1)
                                   WHERE channel_id=$2
                                   """, interaction.guild.id, channel_id)
        except Exception as e:
            log.exception(e)
            await interaction.followup.send(f"There was an error removing {channel_handle} from your subscriptions, please try again.")
        else:
            await interaction.followup.send(f"``{channel_handle}`` has been removed to your subscriptions.")

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name="remove_all_alerts"
    )
    async def remove_all_alerts(self, interaction: discord.Interaction):
        """Removes a guild from a YouTube channel alert.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param channel_handle: the YouTube channel handle to unsubscribe to (@<channel_name>)
        :type channel: discord.TextChannel
        """
        # Defer response
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Update YouTube data
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.youtube
                                   SET subscribed_guilds=ARRAY_REMOVE(subscribed_guilds, $1)
                                   """, interaction.guild.id)
        except Exception as e:
            log.exception(e)
            await interaction.followup.send("There was an error removing all your subscriptions, please try again.")
        else:
            await interaction.followup.send("All subscriptions removeds.")

    @tasks.loop(minutes=10)
    async def check_youtube(self):
        log.info("Checking YouTube channels for new uploads...")

        # Get all YouTube channels
        try:
            async with self.bot.db_pool.acquire() as conn:
                records = await conn.fetch("SELECT * FROM cenbot.youtube")
        except Exception as e:
            log.exception(e)
            return

        # Avoid null dataset
        if records is None:
            log.info("No YouTube channels to check")
            return

        # Iterate through Database
        async for record in forasync(records):
            # Get latest upload
            try:
                async with aiohttp.ClientSession() as session:
                    params = {'key': self.api_key, 'part': "contentDetails, snippet", 'playlistId': record['upload_playlist_id'], 'maxResults': 1, 'order': "date"}
                    async with session.get(self.base_url + "playlistItems", params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            youtube_channel_name = data['items'][0]['snippet']['channelTitle']
                            video_title = data['items'][0]['snippet']['title']
                            date_published = datetime.fromisoformat(data['items'][0]['snippet']['publishedAt'])
                            video_id = data['items'][0]['snippet']['resourceId']['videoId']
                        else:
                            log.error(f"YouTube query {response.url} returned {response.status}: {data['error']['errors'][0]['reason']}")
            except aiohttp.ClientError as e:
                log.exception(e)

            # Compare upload dates
            if record['last_upload_date'] is None or record['last_upload_date'] < date_published:
                # Update database
                try:
                    async with self.bot.db_pool.acquire() as conn:
                        await conn.execute("""
                                           UPDATE cenbot.youtube
                                           SET last_upload_date=$1
                                           WHERE channel_id=$2
                                           """, date_published, record['channel_id'])
                except Exception as e:
                    log.exception(e)
                    continue

                # Check if guilds are still subscribed
                if not record['subscribed_guilds']:
                    # Remove from database
                    try:
                        async with self.bot.db_pool.acquire() as conn:
                            await conn.execute("""
                                               DELETE
                                               FROM cenbot.youtube
                                               WHERE channel_id=$2
                                               """, record['channel_id'])
                    except Exception as e:
                        log.exception(e)
                        continue

                # For for each subscribed guild, send notification
                async for guild_id in forasync(record['subscribed_guilds']):
                    # Get YouTube news channel
                    try:
                        async with self.bot.db_pool.acquire() as conn:
                            record2 = await conn.fetchrow("""
                                                          SELECT youtube_alert_channel
                                                          FROM cenbot.guilds
                                                          WHERE guild_id=$1
                                                          """, guild_id)
                    except Exception as e:
                        log.exception(e)
                        continue

                    # Check for record
                    if record2['youtube_alert_channel']:
                        await self.bot.get_channel(record2['youtube_alert_channel']).send(f"**YouTube Video Alert!**\n{youtube_channel_name} just uploaded a new YouTube video: [{video_title}](https://youtube.com/watch?v={video_id})")

        # Annouce completion
        log.info("Finished checking YouTube channels for new uploads")


# Add to bot
async def setup(bot: cenbot) -> None:
    await bot.add_cog(youtube(bot))