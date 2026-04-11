"""Uses Twitch's API to alert on live streams"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

# Standard library
import os
import time
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

log = getLogger('CENBot.twitch')


class TwitchAlertChannelSelect(discord.ui.ChannelSelect):
    """Saves the chosen text channel as the guild's Twitch live alert channel."""

    def __init__(self, bot: CENBot, current_channel_id: int | None) -> None:
        """Initialise with the currently configured alert channel pre-selected.

        :param bot: the bot instance
        :type bot: CENBot
        :param current_channel_id: the ID of the currently set channel, or ``None``
        :type current_channel_id: int | None
        """
        default_values = [discord.Object(id=current_channel_id)] if current_channel_id else []
        super().__init__(
            placeholder="Select an alert channel...",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            default_values=default_values,
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        """Persist the selected alert channel and confirm to the user.

        :param interaction: the discord interaction triggered by the select
        :type interaction: discord.Interaction
        """
        new_channel_id = self.values[0].id if self.values else None
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET twitch_alert_channel=$2
                                   WHERE id=$1
                                   """, interaction.guild.id, new_channel_id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error saving the channel, please try again.", ephemeral=True)
            return
        if new_channel_id:
            await interaction.response.send_message(f"Alert channel set to {self.values[0].mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("Alert channel cleared.", ephemeral=True)


class TwitchAlertRoleSelect(discord.ui.RoleSelect):
    """Saves the chosen role as the guild's Twitch alert mention role."""

    def __init__(self, bot: CENBot, current_role_id: int | None) -> None:
        """Initialise with the currently configured alert role pre-selected.

        :param bot: the bot instance
        :type bot: CENBot
        :param current_role_id: the ID of the currently set role, or ``None``
        :type current_role_id: int | None
        """
        default_values = [discord.Object(id=current_role_id)] if current_role_id else []
        super().__init__(
            placeholder="Select an alert role...",
            min_values=0,
            max_values=1,
            default_values=default_values,
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        """Persist the selected alert role and confirm to the user.

        :param interaction: the discord interaction triggered by the select
        :type interaction: discord.Interaction
        """
        new_role_id = self.values[0].id if self.values else None
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET twitch_alert_role=$2
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


class TwitchConfigView(discord.ui.LayoutView):
    """Layout view combining the alert channel and alert role selects."""

    def __init__(self, bot: CENBot, channel_id: int | None, role_id: int | None) -> None:
        """Build the config panel with current settings pre-populated.

        :param bot: the bot instance
        :type bot: CENBot
        :param channel_id: currently configured alert channel ID, or ``None``
        :type channel_id: int | None
        :param role_id: currently configured alert role ID, or ``None``
        :type role_id: int | None
        """
        super().__init__()
        self.add_item(discord.ui.TextDisplay("**Alert Channel**"))
        self.add_item(discord.ui.ActionRow(TwitchAlertChannelSelect(bot, channel_id)))
        self.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        self.add_item(discord.ui.TextDisplay("**Alert Role**"))
        self.add_item(discord.ui.ActionRow(TwitchAlertRoleSelect(bot, role_id)))


@app_commands.guild_only()
class Twitch(commands.GroupCog, name="twitch"):
    """Twitch live stream alert operations."""
    def __init__(self, bot: CENBot) -> None:
        self.bot = bot
        self.base_url = "https://api.twitch.tv/helix/"
        self.client_id = os.getenv("TWITCH_CLIENT")
        self.client_secret = os.getenv("TWITCH_SECRET")
        self._token: str | None = None
        self._token_expires: float = 0
        super().__init__()

    def cog_load(self) -> None:
        """Start the Twitch polling task loop."""
        self.check_twitch.start()

    def cog_unload(self) -> None:
        """Stop the Twitch polling task loop."""
        self.check_twitch.stop()

    async def _get_token(self, session: aiohttp.ClientSession) -> str:
        """Returns a valid app access token, fetching a new one if expired.

        :param session: the aiohttp client session
        :type session: aiohttp.ClientSession
        :returns: the app access token
        :rtype: str
        """
        if self._token and time.time() < self._token_expires:
            return self._token

        async with session.post("https://id.twitch.tv/oauth2/token", data={
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
        }) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise aiohttp.ClientError(f"Twitch token fetch failed: {data}")
            self._token = data['access_token']
            self._token_expires = time.time() + data['expires_in'] - 60
            return self._token

    async def _resolve_channel(self, session: aiohttp.ClientSession, query: str) -> tuple[str, str, str] | None:
        """Resolves a Twitch channel URL or login to (user_id, login, display_name).

        Accepts:
        - Twitch channel URLs (``twitch.tv/username``)
        - Usernames

        :param session: the aiohttp client session
        :type session: aiohttp.ClientSession
        :param query: the channel URL or username
        :type query: str
        :returns: (user_id, login, display_name) or None if not found
        :rtype: tuple[str, str, str] | None
        """
        query = query.strip()

        if 'twitch.tv' in query:
            if '://' not in query:
                query = 'https://' + query
            login = urlparse(query).path.strip('/').split('/')[0].lower()
        else:
            login = query.lstrip('@').lower()

        token = await self._get_token(session)
        headers = {'Client-ID': self.client_id, 'Authorization': f'Bearer {token}'}

        async with session.get(self.base_url + "users", params={'login': login}, headers=headers) as resp:
            data = await resp.json()
            if resp.status != 200 or not data.get('data'):
                log.error(f"Twitch user lookup returned {resp.status} for query: {query!r}")
                return None
            user = data['data'][0]
            return user['id'], user['login'], user['display_name']

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def enable(self, interaction: discord.Interaction) -> None:
        """Enables Twitch live alerts.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET twitch_enabled=true
                                   WHERE id=$1
                                   """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Twitch alerts enabled.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def disable(self, interaction: discord.Interaction) -> None:
        """Disables Twitch live alerts.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET twitch_enabled=false
                                   WHERE id=$1
                                   """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Twitch alerts disabled.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def configure(self, interaction: discord.Interaction) -> None:
        """Opens the Twitch configuration view.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT twitch_alert_channel, twitch_alert_role
                                             FROM cenbot.guilds
                                             WHERE id=$1
                                             """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching your settings, please try again.", ephemeral=True)
            return

        channel_id = record['twitch_alert_channel'] if record else None
        role_id = record['twitch_alert_role'] if record else None

        view = TwitchConfigView(self.bot, channel_id, role_id)
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def subscribe(self, interaction: discord.Interaction, channel: str) -> None:
        """Subscribes this guild to Twitch live alerts for a channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param channel: the Twitch channel URL or username
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
            await interaction.followup.send("Could not find that Twitch channel. Provide a URL or username.")
            return

        user_id, login, display_name = result

        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.twitch_channels (channel_id, channel_login, channel_name)
                                   VALUES ($1, $2, $3)
                                   ON CONFLICT (channel_id) DO UPDATE
                                     SET channel_login=EXCLUDED.channel_login,
                                         channel_name=EXCLUDED.channel_name
                                   """, user_id, login, display_name)
                await conn.execute("""
                                   INSERT INTO cenbot.twitch_subscriptions (guild_id, channel_id)
                                   VALUES ($1, $2)
                                   ON CONFLICT DO NOTHING
                                   """, interaction.guild.id, user_id)
        except PostgresError as e:
            log.exception(e)
            await interaction.followup.send("There was an error adding that channel to your subscriptions, please try again.")
        else:
            await interaction.followup.send(f"Subscribed to **{display_name}** (`{login}`).")

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def unsubscribe(self, interaction: discord.Interaction, channel: str) -> None:
        """Unsubscribes this guild from Twitch live alerts for a channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param channel: the Twitch channel URL or username
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
            await interaction.followup.send("Could not find that Twitch channel. Provide a URL or username.")
            return

        user_id, _, _ = result

        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   DELETE FROM cenbot.twitch_subscriptions
                                   WHERE guild_id=$1 AND channel_id=$2
                                   """, interaction.guild.id, user_id)
                await conn.execute("""
                                   DELETE FROM cenbot.twitch_channels
                                   WHERE channel_id NOT IN (SELECT channel_id FROM cenbot.twitch_subscriptions)
                                   """)
        except PostgresError as e:
            log.exception(e)
            await interaction.followup.send("There was an error removing that channel from your subscriptions, please try again.")
        else:
            await interaction.followup.send(f"Unsubscribed from **{channel}**.")

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def remove_all_subscriptions(self, interaction: discord.Interaction) -> None:
        """Unsubscribes this guild from all Twitch channel alerts.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   DELETE FROM cenbot.twitch_subscriptions
                                   WHERE guild_id=$1
                                   """, interaction.guild.id)
                await conn.execute("""
                                   DELETE FROM cenbot.twitch_channels
                                   WHERE channel_id NOT IN (SELECT channel_id FROM cenbot.twitch_subscriptions)
                                   """)
        except PostgresError as e:
            log.exception(e)
            await interaction.followup.send("There was an error removing all your subscriptions, please try again.")
        else:
            await interaction.followup.send("All subscriptions removed.")

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def list(self, interaction: discord.Interaction) -> None:
        """Shows Twitch configuration and current subscriptions.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                guild_record = await conn.fetchrow("""
                                                   SELECT twitch_enabled, twitch_alert_channel, twitch_alert_role
                                                   FROM cenbot.guilds
                                                   WHERE id=$1
                                                   """, interaction.guild.id)
                subscriptions = await conn.fetch("""
                                                 SELECT tc.channel_id, tc.channel_login, tc.channel_name, tc.is_live
                                                 FROM cenbot.twitch_channels tc
                                                 JOIN cenbot.twitch_subscriptions ts ON tc.channel_id = ts.channel_id
                                                 WHERE ts.guild_id=$1
                                                 """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching your subscriptions, please try again.", ephemeral=True)
            return

        enabled = guild_record['twitch_enabled'] if guild_record else False
        channel_id = guild_record['twitch_alert_channel'] if guild_record else None
        role_id = guild_record['twitch_alert_role'] if guild_record else None

        embed = discord.Embed(title="Twitch Configuration", color=discord.Color.purple())
        embed.add_field(name="Status", value="Enabled" if enabled else "Disabled", inline=True)

        if channel_id:
            channel = self.bot.get_channel(channel_id)
            embed.add_field(name="Alert Channel", value=channel.mention if channel else f"<#{channel_id}>", inline=True)
        else:
            embed.add_field(name="Alert Channel", value="Not configured", inline=True)

        if role_id:
            embed.add_field(name="Alert Role", value=f"<@&{role_id}>", inline=True)
        else:
            embed.add_field(name="Alert Role", value="Not set", inline=True)

        if subscriptions:
            subs_text = "\n".join(
                f"• {row['channel_name'] or row['channel_login']} (`{row['channel_login']}`)" + (" 🔴 Live" if row['is_live'] else "")
                for row in subscriptions
            )
        else:
            subs_text = "None"
        embed.add_field(name=f"Subscriptions ({len(subscriptions)})", value=subs_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(minutes=3)
    async def check_twitch(self) -> None:
        """Poll subscribed Twitch channels for live status changes.

        Runs every 3 minutes. Batches up to 100 channel IDs per ``/helix/streams``
        call. Fires an alert only on a ``is_live`` false → true transition to avoid
        repeated notifications while a stream is ongoing.
        """
        log.info("Checking Twitch channels for live streams...")

        try:
            async with self.bot.db_pool.acquire() as conn:
                records = await conn.fetch("""
                                           SELECT tc.channel_id, tc.channel_login, tc.channel_name, tc.is_live,
                                                  ts.guild_id, g.twitch_alert_channel, g.twitch_alert_role
                                           FROM cenbot.twitch_channels tc
                                           JOIN cenbot.twitch_subscriptions ts ON tc.channel_id = ts.channel_id
                                           JOIN cenbot.guilds g ON ts.guild_id = g.id
                                           WHERE g.twitch_enabled = true
                                             AND g.twitch_alert_channel IS NOT NULL
                                             AND g.removed_at IS NULL
                                           """)
        except PostgresError as e:
            log.exception(e)
            return

        if not records:
            log.info("No Twitch subscriptions to check")
            return

        sorted_records = sorted(records, key=lambda r: r['channel_id'])
        channel_groups = {cid: list(grp) for cid, grp in groupby(sorted_records, key=lambda r: r['channel_id'])}
        unique_ids = list(channel_groups.keys())

        try:
            async with aiohttp.ClientSession() as session:
                token = await self._get_token(session)
                headers = {'Client-ID': self.client_id, 'Authorization': f'Bearer {token}'}

                live_streams: dict[str, dict] = {}
                for i in range(0, len(unique_ids), 100):
                    batch = unique_ids[i:i + 100]
                    params = [('user_id', cid) for cid in batch]
                    async with session.get(self.base_url + "streams", params=params, headers=headers) as resp:
                        if resp.status != 200:
                            log.error(f"Twitch API returned {resp.status}")
                            return
                        data = await resp.json()
                        for stream in data['data']:
                            live_streams[stream['user_id']] = stream
        except aiohttp.ClientError as e:
            log.exception(e)
            return

        for channel_id, subscribers in channel_groups.items():
            first = subscribers[0]
            was_live = first['is_live']
            stream = live_streams.get(channel_id)
            is_now_live = stream is not None

            if is_now_live == was_live:
                continue

            try:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute("""
                                       UPDATE cenbot.twitch_channels
                                       SET is_live=$1
                                       WHERE channel_id=$2
                                       """, is_now_live, channel_id)
            except PostgresError as e:
                log.exception(e)
                continue

            if is_now_live:
                channel_name = first['channel_name'] or first['channel_login']
                stream_title = stream['title']
                game_name = stream.get('game_name', '')
                url = f"https://twitch.tv/{first['channel_login']}"

                for row in subscribers:
                    alert_channel = self.bot.get_channel(row['twitch_alert_channel'])
                    if alert_channel is None:
                        continue
                    role_mention = f"<@&{row['twitch_alert_role']}> " if row['twitch_alert_role'] else ""
                    msg = f"{role_mention}**Twitch Live Alert!**\n{channel_name} is now live: [{stream_title}]({url})"
                    if game_name:
                        msg += f"\nPlaying: {game_name}"
                    await alert_channel.send(msg)

        log.info("Finished checking Twitch channels for live streams")


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Twitch(bot))
