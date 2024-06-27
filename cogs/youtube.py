__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '1.1.0'
__status__ = 'Production'
__doc__ = """Uses YouTube's API to pull uploads from YouTube"""

# Python imports
import os
import aiohttp
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
log = logging.getLogger('CENBot.youtube')


@app_commands.guild_only()
class youtube(commands.GroupCog, name='youtube'):
    """These are all the YouTube functions.
    """
    def __init__(self, bot: cbot):
        self.bot = bot
        super().__init__()

    def cog_load(self):
        self.check_youtube.start()

    def cog_unload(self):
        self.check_youtube.stop()

    # Set news channel
    @app_commands.command(
        name='setnewschannel',
        description="Sets the channel social news will be sent to."
    )
    @commands.has_role('bot manager')
    async def youtube_setnewschannel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE serverdata SET news_channel=$2 WHERE guild_id=$1", interaction.guild.id, channel.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("News channel set.", ephemeral=False)

    # Add YouTube channel
    @app_commands.command(
        name="addchannel",
        description="Adds a YouTube channel to pull data from."
    )
    @commands.has_role('bot manager')
    async def youtube_addchannel(self, interaction: discord.Interaction, channel_link: str):
        # Parse input (find channel name)
        at_loc = channel_link.find('@')
        if at_loc != -1:
            channel_name = channel_link[at_loc:]
        else:
            await interaction.response.send_message(f"Invalid YouTube channel URL: {channel_link}. Please try again.")

        # Get records to see if YouTube channel in database already
        try:
            async with self.bot.db_pool.acquire() as con:
                record = await con.fetch("SELECT * FROM youtube_channels WHERE channel_link=$1", channel_link)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)

        # If channel doesn't exist
        if record is None:
            # Get YouTube channel id
            try:
                params = {'key': os.getenv("YOUTUBE_KEY"), 'part': "Id", 'forHandle': channel_name}
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://youtube.googleapis.com/youtube/v3/channels", params=params) as resp:
                        if resp.status == 200:
                            content = await resp.json()
                            channel_id = content['items'][0]['id']
                        else:
                            log.error(f"Query {resp.url} returned {resp.status}: {content['error']['errors'][0]['reason']}")
                            interaction.response.send_message("There was an error retrieving channel data. Please try again.")
            except aiohttp.ClientError as e:
                log.error(e)
                await interaction.response.send_message("There was an error finding the channel, please try again.")

            # Get upload playlist Id
            try:
                params = {'key': os.getenv("YOUTUBE_KEY"), 'part': "contentDetails", 'id': channel_id}
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://youtube.googleapis.com/youtube/v3/channels", params=params) as resp:
                        if resp.status == 200:
                            content = await resp.json()
                            upload_playlist_id = content['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            except aiohttp.ClientError as e:
                log.error(e)

            # Add channel and server
            try:
                async with self.bot.db_pool.acquire() as con:
                    await con.execute("INSERT INTO youtube_channels (channel_link, channel_id, upload_playlist_id) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING", channel_link, channel_id, upload_playlist_id)
                    await con.execute("UPDATE youtube_channels SET guild_ids=ARRAY_ADD(server, $1) where channel_link=$2", interaction.guild.id, channel_link)
            except PostgresError as e:
                log.exception(e)
                await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
            except Exception as e:
                log.exception(e)
                await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Channel ``{channel_link}`` added.", ephemeral=False)
        else:
            # Add guild
            try:
                await con.execute("UPDATE youtube_channels SET guild_ids=ARRAY_ADD(server, $1) where channel_link=$2", interaction.guild.id, channel_link)
            except PostgresError as e:
                log.exception(e)
                await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
            except Exception as e:
                log.exception(e)
                await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Channel ``{channel_link}`` added.", ephemeral=False)

    # Remove YouTube channel
    @app_commands.command(
        name="removechannel",
        description="Removes a YouTube channel."
    )
    @commands.has_role('bot manager')
    async def socials_youtube_removechannel(self, interaction: discord.Interaction, channel_link: str):
        # Remove YouTube channel
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE youtube_channels SET guild_ids=ARRAY_REMOVE(guild_ids, $1) WHERE channel_link=$2", interaction.guild.id, channel_link)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Channel ``{channel_link}`` removed.", ephemeral=False)

    # Check YouTube every 10m
    @tasks.loop(minutes=10)
    async def check_youtube(self):
        # Annouce run
        log.info("Checking YouTube channels for new uploads...")

        # Get all available YouTube channels
        try:
            async with self.bot.db_pool.acquire() as con:
                record = await con.fetch("SELECT * FROM youtube_channels")
        except PostgresError as e:
            log.exception(e)
            return

        # Avoid null dataset
        if record is None:
            log.info("No YouTube channels to check")
            return

        # Get and send latest uploads for each guild
        async for rec in forasync(record):
            # Remove empty guild records from table
            if rec['guild_ids'] is None:
                try:
                    async with self.bot.db_pool.acquire() as con:
                        await con.execute("DELETE FROM youtube_channels WHERE channel_id=$1", rec['channel_id'])
                except PostgresError as e:
                    log.exception(e)
                    continue
                except AttributeError as e:
                    log.error(e)
                    continue
                except:
                    continue
            else:
                # Get latest upload date
                try:
                    params = {'key': os.getenv("YOUTUBE_KEY"), 'part': "contentDetails, snippet", 'playlistId': rec['upload_playlist_id'], 'maxResults': 1, 'order': "date"}
                    async with aiohttp.ClientSession() as session:
                        async with session.get("https://youtube.googleapis.com/youtube/v3/playlistItems", params=params) as resp:
                            content = await resp.json()
                            if resp.status == 200:
                                youtube_channel_name = content['items'][0]['snippet']['channelTitle']
                                video_title = content['items'][0]['snippet']['title']
                                date_published = datetime.fromisoformat(content['items'][0]['snippet']['publishedAt'])
                                video_id = content['items'][0]['snippet']['resourceId']['videoId']
                            else:
                                log.error(f"Query {resp.url} returned {resp.status}: {content['error']['errors'][0]['reason']}")
                                continue
                except aiohttp.ClientError as e:
                    log.error(e)
                    return
                except ValueError as e:
                    log.error(e)
                    return

                # Get database upload date
                try:
                    async with self.bot.db_pool.acquire() as con:
                        record = await con.fetch("SELECT last_upload FROM youtube_channels WHERE channel_id=$1", rec['channel_id'])
                    last_upload = record[0]['last_upload']
                except PostgresError as e:
                    log.exception(e)
                    return

                # Compare and update if necessary
                if last_upload is None or last_upload < date_published:
                    try:
                        async with self.bot.db_pool.acquire() as con:
                            await con.execute("UPDATE youtube_channels SET last_upload=$1 WHERE channel_id=$2", date_published, rec['channel_id'])
                    except PostgresError as e:
                        log.exception(e)
                        continue
                    except UnboundLocalError as e:
                        log.exception(e)
                        continue

                    # log
                    log.debug(f"New video found: ID={video_id}")

                    # For each server listed, send new upload alert
                    async for guild_id in forasync(rec['guild_ids']):
                        # Get YouTube news channel
                        try:
                            async with self.bot.db_pool.acquire() as con:
                                record = await con.fetch("SELECT youtube_news_channel FROM serverdata WHERE guild_id=$1", guild_id)
                            channel_id = record[0]['youtube_news_channel']
                        except PostgresError as e:
                            log.exception(e)
                            continue
                        except UnboundLocalError as e:
                            log.exception(e)
                            continue

                        # Send if channel exists
                        if channel_id is not None:
                            # Get channel
                            channel = self.bot.get_channel(channel_id)
                            await channel.send(f"**YouTube Video Alert!**\n{youtube_channel_name} just uploaded a new YouTube video: [{video_title}](https://youtube.com/watch?v={video_id})")

        # Annouce completion
        log.info("Finished checking YouTube channels for new uploads")


async def setup(bot: cbot) -> None:
    await bot.add_cog(youtube(bot))