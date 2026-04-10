"""Uses YouTube's API to pull uploads from YouTube"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "2.0.0"
__status__ = "Production"

# Standard library
import os
from datetime import datetime
from itertools import groupby
from logging import getLogger
from urllib.parse import urlparse

# Third-party
import aiohttp
import discord
from discord.ext import commands, tasks
from discord import app_commands
from asyncpg.exceptions import PostgresError

# Internal
from start import CENBot

log = getLogger('CENBot.youtube')


class YouTubeUploadChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, bot: CENBot, current_channel_id: int | None) -> None:
        default_values = [discord.Object(id=current_channel_id)] if current_channel_id else []
        super().__init__(
            placeholder="Select an upload alert channel...",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            default_values=default_values,
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        new_channel_id = self.values[0].id if self.values else None
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET youtube_upload_alert_channel=$2
                                   WHERE id=$1
                                   """, interaction.guild.id, new_channel_id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error saving the channel, please try again.", ephemeral=True)
            return
        if new_channel_id:
            await interaction.response.send_message(f"Upload alert channel set to {self.values[0].mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("Upload alert channel cleared.", ephemeral=True)


class YouTubeLiveChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, bot: CENBot, current_channel_id: int | None) -> None:
        default_values = [discord.Object(id=current_channel_id)] if current_channel_id else []
        super().__init__(
            placeholder="Select a live alert channel...",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            default_values=default_values,
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        new_channel_id = self.values[0].id if self.values else None
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET youtube_live_alert_channel=$2
                                   WHERE id=$1
                                   """, interaction.guild.id, new_channel_id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error saving the channel, please try again.", ephemeral=True)
            return
        if new_channel_id:
            await interaction.response.send_message(f"Live alert channel set to {self.values[0].mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("Live alert channel cleared.", ephemeral=True)


class YouTubeAlertRoleSelect(discord.ui.RoleSelect):
    def __init__(self, bot: CENBot, current_role_id: int | None) -> None:
        default_values = [discord.Object(id=current_role_id)] if current_role_id else []
        super().__init__(
            placeholder="Select an alert role...",
            min_values=0,
            max_values=1,
            default_values=default_values,
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        new_role_id = self.values[0].id if self.values else None
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET youtube_alert_role=$2
                                   WHERE id=$1
                                   """, interaction.guild.id, new_role_id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error saving the role, please try again.", ephemeral=True)
            return
        if new_role_id:
            await interaction.response.send_message(f"Alert role set to {self.values[0].mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("Alert role cleared.", ephemeral=True)


class YouTubeConfigView(discord.ui.LayoutView):
    def __init__(self, bot: CENBot, upload_channel_id: int | None, live_channel_id: int | None, role_id: int | None) -> None:
        super().__init__()
        self.add_item(discord.ui.TextDisplay("**Upload Alert Channel**"))
        self.add_item(discord.ui.ActionRow(YouTubeUploadChannelSelect(bot, upload_channel_id)))
        self.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        self.add_item(discord.ui.TextDisplay("**Live Alert Channel**"))
        self.add_item(discord.ui.ActionRow(YouTubeLiveChannelSelect(bot, live_channel_id)))
        self.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        self.add_item(discord.ui.TextDisplay("**Alert Role**"))
        self.add_item(discord.ui.ActionRow(YouTubeAlertRoleSelect(bot, role_id)))


@app_commands.guild_only()
class YouTube(commands.GroupCog, name="youtube"):
    """YouTube operations."""
    def __init__(self, bot: CENBot):
        self.bot = bot
        self.base_url = "https://youtube.googleapis.com/youtube/v3/"
        self.api_key = os.getenv("YOUTUBE_KEY")
        super().__init__()

    def cog_load(self):
        self.check_youtube.start()

    def cog_unload(self):
        self.check_youtube.stop()

    async def _resolve_channel(self, session: aiohttp.ClientSession, query: str) -> tuple[str, str] | None:
        """Resolves a channel URL, handle, or ID to (channel_id, upload_playlist_id).

        Accepts:
        - YouTube channel URLs (``youtube.com/@handle``, ``youtube.com/channel/UC...``)
        - Channel handles (``@handle``)
        - Channel IDs (``UC...``)

        :param session: the aiohttp client session
        :type session: aiohttp.ClientSession
        :param query: the channel URL, handle, or ID
        :type query: str
        :returns: (channel_id, upload_playlist_id, channel_name) or None if not found
        :rtype: tuple[str, str, str] | None
        """
        params = {'key': self.api_key, 'part': "id,snippet,contentDetails"}
        query = query.strip()

        if '://' in query or 'youtube.com' in query:
            if '://' not in query:
                query = 'https://' + query
            path = urlparse(query).path.rstrip('/')
            if path.startswith('/@'):
                params['forHandle'] = path[1:]
            elif '/channel/' in path:
                params['id'] = path.split('/channel/')[1].split('/')[0]
            elif path.startswith('/c/') or path.startswith('/user/'):
                params['forHandle'] = '@' + path.rsplit('/', 1)[-1]
            else:
                return None
        elif query.startswith('@'):
            params['forHandle'] = query
        elif query.startswith('UC') and len(query) == 24:
            params['id'] = query
        else:
            params['forHandle'] = '@' + query

        async with session.get(self.base_url + "channels", params=params) as response:
            data = await response.json()
            if response.status != 200 or not data.get('items'):
                log.error(f"YouTube channel lookup returned {response.status} for query: {query!r}")
                return None
            item = data['items'][0]
            channel_name = item['snippet']['title']
            return item['id'], item['contentDetails']['relatedPlaylists']['uploads'], channel_name

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def enable(self, interaction: discord.Interaction) -> None:
        """Enables YouTube alerts.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET youtube_enabled=true
                                   WHERE id=$1
                                   """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("YouTube alerts enabled.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def disable(self, interaction: discord.Interaction) -> None:
        """Disables YouTube alerts.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET youtube_enabled=false
                                   WHERE id=$1
                                   """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("YouTube alerts disabled.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def configure(self, interaction: discord.Interaction) -> None:
        """Opens the YouTube configuration view.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT youtube_upload_alert_channel, youtube_live_alert_channel, youtube_alert_role
                                             FROM cenbot.guilds
                                             WHERE id=$1
                                             """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching your settings, please try again.", ephemeral=True)
            return

        upload_channel_id = record['youtube_upload_alert_channel'] if record else None
        live_channel_id = record['youtube_live_alert_channel'] if record else None
        role_id = record['youtube_alert_role'] if record else None

        view = YouTubeConfigView(self.bot, upload_channel_id, live_channel_id, role_id)
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def subscribe(self, interaction: discord.Interaction, channel: str) -> None:
        """Subscribes this guild to YouTube upload alerts for a channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param channel: the YouTube channel URL, handle (@name), or channel ID
        :type channel: str
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            async with aiohttp.ClientSession() as session:
                result = await self._resolve_channel(session, channel)
        except aiohttp.ClientError as e:
            log.exception(e)
            await interaction.followup.send("There was an error retrieving the channel, please try again.")
            return

        if result is None:
            await interaction.followup.send("Could not find that YouTube channel. Provide a URL, handle (``@name``), or channel ID.")
            return

        channel_id, upload_playlist_id, channel_name = result

        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.youtube_channels (channel_id, upload_playlist_id, channel_name)
                                   VALUES ($1, $2, $3)
                                   ON CONFLICT (channel_id) DO UPDATE SET channel_name=EXCLUDED.channel_name
                                   """, channel_id, upload_playlist_id, channel_name)
                await conn.execute("""
                                   INSERT INTO cenbot.youtube_subscriptions (guild_id, channel_id)
                                   VALUES ($1, $2)
                                   ON CONFLICT DO NOTHING
                                   """, interaction.guild.id, channel_id)
        except PostgresError as e:
            log.exception(e)
            await interaction.followup.send("There was an error adding that channel to your subscriptions, please try again.")
        else:
            await interaction.followup.send(f"``{channel}`` has been added to your subscriptions.")

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def unsubscribe(self, interaction: discord.Interaction, channel: str) -> None:
        """Unsubscribes this guild from YouTube upload alerts for a channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param channel: the YouTube channel URL, handle (@name), or channel ID
        :type channel: str
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            async with aiohttp.ClientSession() as session:
                result = await self._resolve_channel(session, channel)
        except aiohttp.ClientError as e:
            log.exception(e)
            await interaction.followup.send("There was an error retrieving the channel, please try again.")
            return

        if result is None:
            await interaction.followup.send("Could not find that YouTube channel. Provide a URL, handle (``@name``), or channel ID.")
            return

        channel_id, _, _name = result

        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   DELETE FROM cenbot.youtube_subscriptions
                                   WHERE guild_id=$1 AND channel_id=$2
                                   """, interaction.guild.id, channel_id)
                await conn.execute("""
                                   DELETE FROM cenbot.youtube_channels
                                   WHERE channel_id NOT IN (SELECT channel_id FROM cenbot.youtube_subscriptions)
                                   """)
        except PostgresError as e:
            log.exception(e)
            await interaction.followup.send("There was an error removing that channel from your subscriptions, please try again.")
        else:
            await interaction.followup.send(f"``{channel}`` has been removed from your subscriptions.")

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def remove_all_subscriptions(self, interaction: discord.Interaction) -> None:
        """Unsubscribes this guild from all YouTube channel alerts.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   DELETE FROM cenbot.youtube_subscriptions
                                   WHERE guild_id=$1
                                   """, interaction.guild.id)
                await conn.execute("""
                                   DELETE FROM cenbot.youtube_channels
                                   WHERE channel_id NOT IN (SELECT channel_id FROM cenbot.youtube_subscriptions)
                                   """)
        except PostgresError as e:
            log.exception(e)
            await interaction.followup.send("There was an error removing all your subscriptions, please try again.")
        else:
            await interaction.followup.send("All subscriptions removed.")

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def list(self, interaction: discord.Interaction) -> None:
        """Shows YouTube configuration and current subscriptions.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                guild_record = await conn.fetchrow("""
                                                   SELECT youtube_enabled, youtube_upload_alert_channel,
                                                          youtube_live_alert_channel, youtube_alert_role
                                                   FROM cenbot.guilds
                                                   WHERE id=$1
                                                   """, interaction.guild.id)
                subscriptions = await conn.fetch("""
                                                 SELECT yc.channel_id, yc.channel_name
                                                 FROM cenbot.youtube_channels yc
                                                 JOIN cenbot.youtube_subscriptions ys ON yc.channel_id = ys.channel_id
                                                 WHERE ys.guild_id=$1
                                                 """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching your subscriptions, please try again.", ephemeral=True)
            return

        enabled = guild_record['youtube_enabled'] if guild_record else False
        upload_channel_id = guild_record['youtube_upload_alert_channel'] if guild_record else None
        live_channel_id = guild_record['youtube_live_alert_channel'] if guild_record else None
        alert_role_id = guild_record['youtube_alert_role'] if guild_record else None

        embed = discord.Embed(title="YouTube Configuration", color=discord.Color.red())
        embed.add_field(name="Status", value="Enabled" if enabled else "Disabled", inline=True)

        if upload_channel_id:
            channel = self.bot.get_channel(upload_channel_id)
            embed.add_field(name="Upload Channel", value=channel.mention if channel else f"<#{upload_channel_id}>", inline=True)
        else:
            embed.add_field(name="Upload Channel", value="Not configured", inline=True)

        if live_channel_id:
            channel = self.bot.get_channel(live_channel_id)
            embed.add_field(name="Live Channel", value=channel.mention if channel else f"<#{live_channel_id}>", inline=True)
        else:
            embed.add_field(name="Live Channel", value="Not configured", inline=True)

        if alert_role_id:
            embed.add_field(name="Alert Role", value=f"<@&{alert_role_id}>", inline=True)
        else:
            embed.add_field(name="Alert Role", value="Not set", inline=True)

        if subscriptions:
            subs_text = "\n".join(
                f"• {row['channel_name'] or row['channel_id']} (`{row['channel_id']}`)"
                for row in subscriptions
            )
        else:
            subs_text = "None"
        embed.add_field(name=f"Subscriptions ({len(subscriptions)})", value=subs_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(minutes=10)
    async def check_youtube(self):
        log.info("Checking YouTube channels for new uploads...")

        try:
            async with self.bot.db_pool.acquire() as conn:
                records = await conn.fetch("""
                                           SELECT yc.channel_id, yc.upload_playlist_id, yc.last_upload_date,
                                                  ys.guild_id, g.youtube_upload_alert_channel,
                                                  g.youtube_live_alert_channel, g.youtube_alert_role
                                           FROM cenbot.youtube_channels yc
                                           JOIN cenbot.youtube_subscriptions ys ON yc.channel_id = ys.channel_id
                                           JOIN cenbot.guilds g ON ys.guild_id = g.id
                                           WHERE g.youtube_enabled = true
                                             AND (g.youtube_upload_alert_channel IS NOT NULL OR g.youtube_live_alert_channel IS NOT NULL)
                                             AND g.removed_at IS NULL
                                           """)
        except PostgresError as e:
            log.exception(e)
            return

        if not records:
            log.info("No YouTube subscriptions to check")
            return

        sorted_records = sorted(records, key=lambda r: r['channel_id'])
        for channel_id, group in groupby(sorted_records, key=lambda r: r['channel_id']):
            subscribers = list(group)
            record = subscribers[0]

            try:
                async with aiohttp.ClientSession() as session:
                    params = {
                        'key': self.api_key,
                        'part': "snippet",
                        'playlistId': record['upload_playlist_id'],
                        'maxResults': 1,
                    }
                    async with session.get(self.base_url + "playlistItems", params=params) as response:
                        data = await response.json()
                        if response.status != 200:
                            log.error(f"YouTube API returned {response.status}: {data['error']['errors'][0]['reason']}")
                            continue
                        item = data['items'][0]['snippet']
                        youtube_channel_name = item['channelTitle']
                        video_title: str = item['title']
                        date_published = datetime.fromisoformat(item['publishedAt'])
                        video_id = item['resourceId']['videoId']
            except aiohttp.ClientError as e:
                log.exception(e)
                continue

            if record['last_upload_date'] is not None and record['last_upload_date'] >= date_published:
                continue

            try:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute("""
                                       UPDATE cenbot.youtube_channels
                                       SET last_upload_date=$1
                                       WHERE channel_id=$2
                                       """, date_published, channel_id)
            except PostgresError as e:
                log.exception(e)
                continue

            is_live = "🔴" in video_title
            video_title = video_title.replace("🔴 ", "").replace("🔴", "").strip()

            for row in subscribers:
                role_mention = f"<@&{row['youtube_alert_role']}> " if row['youtube_alert_role'] else ""
                if is_live:
                    live_channel_id = row['youtube_live_alert_channel'] or row['youtube_upload_alert_channel']
                    if live_channel_id is None:
                        continue
                    alert_channel = self.bot.get_channel(live_channel_id)
                    if alert_channel is None:
                        continue
                    await alert_channel.send(f"{role_mention}**YouTube Livestream Alert!**\n{youtube_channel_name} is live: [{video_title}](https://youtube.com/watch?v={video_id})")
                else:
                    if row['youtube_upload_alert_channel'] is None:
                        continue
                    alert_channel = self.bot.get_channel(row['youtube_upload_alert_channel'])
                    if alert_channel is None:
                        continue
                    await alert_channel.send(f"{role_mention}**YouTube Video Alert!**\n{youtube_channel_name} just uploaded a new video: [{video_title}](https://youtube.com/watch?v={video_id})")

        log.info("Finished checking YouTube channels for new uploads")


async def setup(bot: CENBot) -> None:
    await bot.add_cog(YouTube(bot))
