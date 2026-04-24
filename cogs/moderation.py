"""Guild activity logging and moderation"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "2.0.0"
__status__ = "Production"

# Standard library
from dataclasses import dataclass
from logging import getLogger

# Third-party
import discord
from discord.ext import commands
from discord import app_commands
from asyncpg.exceptions import PostgresError

# Internal
from start import CENBot
from utils.embeds import timestamp_footer, BRAND_COLOR

log = getLogger('CENBot.moderation')

# ---------------------------------------------------------------------------
# Moderation levels
# ---------------------------------------------------------------------------
# 0 — Off       : no logging, no reports, no new-member protection
# 1 — Reports   : context-menu reports → report channel
#                 new-member message timeout (if configured)
# 2 — Messages  : level 1 + message edits + message deletes → log channel
# 3 — Members   : level 2 + voice join/leave/move + member join/leave
#                 + nickname changes → log channel
# 4 — Server    : level 3 + bans/unbans + role create/delete → log channel
# ---------------------------------------------------------------------------

LEVEL_NAMES = {0: "Off", 1: "Reports", 2: "Messages", 3: "Members", 4: "Server"}


@dataclass
class ModerationConfig:
    """Cached per-guild moderation settings.

    Populated from ``cenbot.guilds`` at cog load and updated in-place
    whenever a config command writes a new value to the database.
    """
    level: int = 0
    log_channel: int | None = None
    report_channel: int | None = None
    new_member_timeout: int = 0   # seconds; 0 = disabled


# ---------------------------------------------------------------------------
# UI — configuration view
# ---------------------------------------------------------------------------

class LogChannelSelect(discord.ui.ChannelSelect):
    """Saves the chosen text channel as the guild's moderation log channel."""

    def __init__(self, cog: 'Moderation', guild_id: int, current: int | None) -> None:
        """Initialise the select with the currently configured log channel pre-selected.

        :param cog: the owning Moderation cog (for cache access)
        :type cog: Moderation
        :param guild_id: the guild this select is being shown for
        :type guild_id: int
        :param current: the ID of the currently set log channel, or ``None``
        :type current: int | None
        """
        default_values = [discord.Object(id=current)] if current else []
        super().__init__(
            placeholder="Select a log channel...",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            default_values=default_values,
        )
        self.cog = cog
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction) -> None:
        """Persist the selected log channel, update the cache, and confirm.

        :param interaction: the discord interaction triggered by the select
        :type interaction: discord.Interaction
        """
        new_channel_id = self.values[0].id if self.values else None
        try:
            async with self.cog.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET moderation_log_channel=$2
                                   WHERE id=$1
                                   """, self.guild_id, new_channel_id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("Error saving log channel, please try again.", ephemeral=True)
            return

        # Update in-memory cache so event handlers see the change immediately
        self.cog._config.setdefault(self.guild_id, ModerationConfig()).log_channel = new_channel_id

        if new_channel_id:
            await interaction.response.send_message(f"Log channel set to {self.values[0].mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("Log channel cleared.", ephemeral=True)


class ReportChannelSelect(discord.ui.ChannelSelect):
    """Saves the chosen text channel as the guild's report destination."""

    def __init__(self, cog: 'Moderation', guild_id: int, current: int | None) -> None:
        """Initialise the select with the currently configured report channel pre-selected.

        :param cog: the owning Moderation cog (for cache access)
        :type cog: Moderation
        :param guild_id: the guild this select is being shown for
        :type guild_id: int
        :param current: the ID of the currently set report channel, or ``None``
        :type current: int | None
        """
        default_values = [discord.Object(id=current)] if current else []
        super().__init__(
            placeholder="Select a report channel...",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            default_values=default_values,
        )
        self.cog = cog
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction) -> None:
        """Persist the selected report channel, update the cache, and confirm.

        :param interaction: the discord interaction triggered by the select
        :type interaction: discord.Interaction
        """
        new_channel_id = self.values[0].id if self.values else None
        try:
            async with self.cog.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET moderation_report_channel=$2
                                   WHERE id=$1
                                   """, self.guild_id, new_channel_id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("Error saving report channel, please try again.", ephemeral=True)
            return

        self.cog._config.setdefault(self.guild_id, ModerationConfig()).report_channel = new_channel_id

        if new_channel_id:
            await interaction.response.send_message(f"Report channel set to {self.values[0].mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("Report channel cleared.", ephemeral=True)


class ModerationLevelSelect(discord.ui.Select):
    """Saves the chosen moderation level for the guild."""

    def __init__(self, cog: 'Moderation', guild_id: int, current_level: int) -> None:
        """Initialise the select with the current moderation level pre-selected.

        :param cog: the owning Moderation cog (for cache access)
        :type cog: Moderation
        :param guild_id: the guild this select is being shown for
        :type guild_id: int
        :param current_level: the currently active moderation level (0–4)
        :type current_level: int
        """
        options = [
            discord.SelectOption(
                label="0 — Off",
                value="0",
                description="No logging, reports, or new-member protection.",
                default=(current_level == 0),
            ),
            discord.SelectOption(
                label="1 — Reports",
                value="1",
                description="User reports + new-member message timeout.",
                default=(current_level == 1),
            ),
            discord.SelectOption(
                label="2 — Messages",
                value="2",
                description="Level 1 + message edits and deletes.",
                default=(current_level == 2),
            ),
            discord.SelectOption(
                label="3 — Members",
                value="3",
                description="Level 2 + voice state and member join/leave.",
                default=(current_level == 3),
            ),
            discord.SelectOption(
                label="4 — Server",
                value="4",
                description="Level 3 + bans, unbans, and role create/delete.",
                default=(current_level == 4),
            ),
        ]
        super().__init__(placeholder="Select a moderation level...", options=options)
        self.cog = cog
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction) -> None:
        """Persist the selected moderation level, update the cache, and confirm.

        :param interaction: the discord interaction triggered by the select
        :type interaction: discord.Interaction
        """
        new_level = int(self.values[0])
        try:
            async with self.cog.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET moderation_level=$2
                                   WHERE id=$1
                                   """, self.guild_id, new_level)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("Error saving moderation level, please try again.", ephemeral=True)
            return

        self.cog._config.setdefault(self.guild_id, ModerationConfig()).level = new_level
        await interaction.response.send_message(
            f"Moderation level set to **{new_level} — {LEVEL_NAMES[new_level]}**.", ephemeral=True
        )


class ModerationConfigView(discord.ui.View):
    """Combines the three moderation selects into a single ephemeral config panel."""

    def __init__(self, cog: 'Moderation', guild_id: int, config: ModerationConfig) -> None:
        """Build the config panel from the guild's current moderation settings.

        :param cog: the owning Moderation cog
        :type cog: Moderation
        :param guild_id: the guild this panel is being shown for
        :type guild_id: int
        :param config: the guild's current cached moderation config
        :type config: ModerationConfig
        """
        super().__init__()
        self.add_item(LogChannelSelect(cog, guild_id, config.log_channel))
        self.add_item(ReportChannelSelect(cog, guild_id, config.report_channel))
        self.add_item(ModerationLevelSelect(cog, guild_id, config.level))


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

@app_commands.guild_only()
class Moderation(commands.GroupCog, name="moderation"):
    """Guild activity logging and moderation."""

    def __init__(self, bot: CENBot) -> None:
        """Initialise the cog, prepare the config cache, and create context menu objects.

        Context menus are registered with the command tree in :meth:`cog_load`
        and removed in :meth:`cog_unload` to prevent duplicate entries on reload.

        :param bot: the bot instance
        :type bot: CENBot
        """
        self.bot = bot
        # Keyed by guild ID; populated on cog_load, mutated on config changes.
        # Event handlers read from here — zero DB queries during normal operation.
        self._config: dict[int, ModerationConfig] = {}

        self.ctx_report_message = app_commands.ContextMenu(
            name="Report Message",
            callback=self.report_message,
        )
        self.ctx_report_user = app_commands.ContextMenu(
            name="Report User",
            callback=self.report_user,
        )
        super().__init__()

    async def cog_load(self) -> None:
        """Populate the in-memory config cache and register context menus."""
        try:
            async with self.bot.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                                        SELECT id,
                                               moderation_level,
                                               moderation_log_channel,
                                               moderation_report_channel,
                                               moderation_new_member_timeout
                                        FROM cenbot.guilds
                                        WHERE removed_at IS NULL
                                        """)
            for row in rows:
                self._config[row['id']] = ModerationConfig(
                    level=row['moderation_level'] or 0,
                    log_channel=row['moderation_log_channel'],
                    report_channel=row['moderation_report_channel'],
                    new_member_timeout=row['moderation_new_member_timeout'] or 0,
                )
            log.info(f"Moderation config cached for {len(self._config)} guild(s)")
        except PostgresError as e:
            log.exception(e)

        self.bot.tree.add_command(self.ctx_report_message)
        self.bot.tree.add_command(self.ctx_report_user)

    async def cog_unload(self) -> None:
        """Deregister context menus to avoid duplicate entries on reload."""
        self.bot.tree.remove_command(self.ctx_report_message.name, type=self.ctx_report_message.type)
        self.bot.tree.remove_command(self.ctx_report_user.name, type=self.ctx_report_user.type)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_config(self, guild_id: int) -> ModerationConfig:
        """Return the cached config for a guild, or a safe default (level 0).

        :param guild_id: the guild's ID
        :type guild_id: int
        :returns: the guild's moderation config
        :rtype: ModerationConfig
        """
        return self._config.get(guild_id, ModerationConfig())

    async def _send_log(self, guild_id: int, embed: discord.Embed) -> None:
        """Send an embed to the guild's configured log channel.

        Silently skips if no log channel is configured or the channel cannot
        be resolved (e.g. deleted since config was last saved).

        :param guild_id: the guild's ID
        :type guild_id: int
        :param embed: the embed to send
        :type embed: discord.Embed
        """
        config = self._get_config(guild_id)
        if not config.log_channel:
            return
        channel = self.bot.get_channel(config.log_channel)
        if not channel:
            log.warning(f"Log channel {config.log_channel} not found for guild {guild_id}")
            return
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            log.warning(f"Missing permissions to send to log channel {config.log_channel} in guild {guild_id}")

    async def _send_report(self, guild_id: int, embed: discord.Embed) -> None:
        """Send an embed to the guild's configured report channel.

        :param guild_id: the guild's ID
        :type guild_id: int
        :param embed: the embed to send
        :type embed: discord.Embed
        """
        config = self._get_config(guild_id)
        if not config.report_channel:
            return
        channel = self.bot.get_channel(config.report_channel)
        if not channel:
            log.warning(f"Report channel {config.report_channel} not found for guild {guild_id}")
            return
        try:
            await channel.send(content="@here", embed=embed)
        except discord.Forbidden:
            log.warning(f"Missing permissions to send to report channel {config.report_channel} in guild {guild_id}")

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(name="configure", description="Configure moderation logging and level")
    async def configure(self, interaction: discord.Interaction) -> None:
        """Open an interactive panel to set log/report channels and moderation level.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        config = self._get_config(interaction.guild.id)
        view = ModerationConfigView(self, interaction.guild.id, config)

        embed = discord.Embed(title="Moderation Configuration", color=BRAND_COLOR)
        embed.add_field(
            name="Log Channel",
            value=f"<#{config.log_channel}>" if config.log_channel else "Not set",
            inline=True,
        )
        embed.add_field(
            name="Report Channel",
            value=f"<#{config.report_channel}>" if config.report_channel else "Not set",
            inline=True,
        )
        embed.add_field(
            name="Level",
            value=f"**{config.level}** — {LEVEL_NAMES[config.level]}",
            inline=True,
        )
        embed.set_footer(text="Changes take effect immediately.")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(name="timeout", description="Set how long (seconds) new members are blocked from sending messages")
    @app_commands.describe(seconds="Duration in seconds; 0 to disable")
    async def timeout_cmd(self, interaction: discord.Interaction, seconds: int) -> None:
        """Configure the new-member message timeout (active at level 1+).

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param seconds: seconds a new member must wait before messaging; 0 disables
        :type seconds: int
        """
        if seconds < 0:
            await interaction.response.send_message("Timeout must be 0 or greater.", ephemeral=True)
            return
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET moderation_new_member_timeout=$2
                                   WHERE id=$1
                                   """, interaction.guild.id, seconds)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("Error saving timeout, please try again.", ephemeral=True)
            return

        self._config.setdefault(interaction.guild.id, ModerationConfig()).new_member_timeout = seconds

        if seconds == 0:
            await interaction.response.send_message("New-member message timeout disabled.", ephemeral=True)
        else:
            await interaction.response.send_message(
                f"New-member message timeout set to **{seconds}s**.", ephemeral=True
            )

    # ------------------------------------------------------------------
    # Context menus (level 1+)
    # ------------------------------------------------------------------

    async def report_message(self, interaction: discord.Interaction, msg: discord.Message) -> None:
        """Report a message to the guild's report channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param msg: the message being reported
        :type msg: discord.Message
        """
        await interaction.response.defer(ephemeral=True)
        config = self._get_config(interaction.guild.id)
        if config.level < 1 or not config.report_channel:
            await interaction.followup.send("Reporting is not enabled on this server.", ephemeral=True)
            return

        embed = discord.Embed(title="Message Report", colour=discord.Colour.red())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)
        embed.add_field(name="Reported by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Author", value=msg.author.mention, inline=True)
        embed.add_field(name="Channel", value=msg.channel.mention, inline=True)
        if msg.content:
            embed.add_field(name="Content", value=msg.content[:1024], inline=False)
        embed.add_field(name="Link", value=f"[Jump to message]({msg.jump_url})", inline=False)
        timestamp_footer(embed)

        await self._send_report(interaction.guild.id, embed)
        await interaction.followup.send("Message reported.", ephemeral=True)

    async def report_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        """Report a user to the guild's report channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param member: the member being reported
        :type member: discord.Member
        """
        await interaction.response.defer(ephemeral=True)
        config = self._get_config(interaction.guild.id)
        if config.level < 1 or not config.report_channel:
            await interaction.followup.send("Reporting is not enabled on this server.", ephemeral=True)
            return

        embed = discord.Embed(title="User Report", colour=discord.Colour.red())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Reported by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reported user", value=f"{member.mention} (`{member}`)", inline=True)
        embed.add_field(name="Channel", value=interaction.channel.mention, inline=True)
        timestamp_footer(embed)

        await self._send_report(interaction.guild.id, embed)
        await interaction.followup.send("User reported.", ephemeral=True)

    # ------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        """Delete messages from members who joined too recently (level 1+).

        :param msg: the incoming message
        :type msg: discord.Message
        """
        if msg.author == self.bot.user or not msg.guild:
            return

        config = self._get_config(msg.guild.id)
        if config.level < 1 or config.new_member_timeout == 0:
            return
        if msg.author.joined_at is None:
            return

        age = (discord.utils.utcnow() - msg.author.joined_at).total_seconds()
        if age < config.new_member_timeout:
            remaining = int(config.new_member_timeout - age)
            try:
                await msg.delete()
                await msg.author.send(
                    f"Your message in **{msg.guild.name}** was removed because your account joined too recently. "
                    f"Please wait **{remaining}s** more before sending messages."
                )
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """Log message edits to the log channel (level 2+).

        :param before: message content before the edit
        :type before: discord.Message
        :param after: message content after the edit
        :type after: discord.Message
        """
        if before.author == self.bot.user or not before.guild:
            return
        if before.content == after.content:
            return  # embed unfurl — no actual text change

        config = self._get_config(before.guild.id)
        if config.level < 2:
            return

        embed = discord.Embed(title="Message Edited", colour=discord.Colour.yellow())
        embed.set_author(name=before.author.display_name, icon_url=before.author.display_avatar)
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Link", value=f"[Jump]({after.jump_url})", inline=True)
        embed.add_field(name="Before", value=before.content[:1024] or "*empty*", inline=False)
        embed.add_field(name="After", value=after.content[:1024] or "*empty*", inline=False)
        timestamp_footer(embed)

        await self._send_log(before.guild.id, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message) -> None:
        """Log message deletions to the log channel (level 2+).

        :param msg: the deleted message
        :type msg: discord.Message
        """
        if msg.author == self.bot.user or not msg.guild:
            return

        config = self._get_config(msg.guild.id)
        if config.level < 2:
            return

        embed = discord.Embed(title="Message Deleted", colour=discord.Colour.orange())
        embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar)
        embed.add_field(name="Author", value=msg.author.mention, inline=True)
        embed.add_field(name="Channel", value=msg.channel.mention, inline=True)
        embed.add_field(name="Content", value=msg.content[:1024] or "*no text content*", inline=False)
        timestamp_footer(embed)

        await self._send_log(msg.guild.id, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Log voice channel joins, leaves, and moves (level 3+).

        :param member: the member whose voice state changed
        :type member: discord.Member
        :param before: voice state before the change
        :type before: discord.VoiceState
        :param after: voice state after the change
        :type after: discord.VoiceState
        """
        if member == self.bot.user:
            return
        if before.channel == after.channel:
            return  # mute/deafen/stream change only — not a channel transition

        config = self._get_config(member.guild.id)
        if config.level < 3:
            return

        if before.channel is None:
            colour = discord.Colour.green()
            description = f"{member.mention} joined {after.channel.mention}"
        elif after.channel is None:
            colour = discord.Colour.red()
            description = f"{member.mention} left {before.channel.mention}"
        else:
            colour = discord.Colour.yellow()
            description = f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}"

        embed = discord.Embed(title="Voice State", description=description, colour=colour)
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        timestamp_footer(embed)

        await self._send_log(member.guild.id, embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Log new member joins to the log channel (level 3+).

        :param member: the member who joined
        :type member: discord.Member
        """
        config = self._get_config(member.guild.id)
        if config.level < 3:
            return

        embed = discord.Embed(title="Member Joined", colour=discord.Colour.green())
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        embed.add_field(name="User", value=f"{member.mention} (`{member}`)", inline=False)
        embed.add_field(
            name="Account Created",
            value=discord.utils.format_dt(member.created_at, 'R'),
            inline=True,
        )
        timestamp_footer(embed)

        await self._send_log(member.guild.id, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Log member departures to the log channel (level 3+).

        :param member: the member who left or was removed
        :type member: discord.Member
        """
        config = self._get_config(member.guild.id)
        if config.level < 3:
            return

        embed = discord.Embed(title="Member Left", colour=discord.Colour.red())
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        embed.add_field(name="User", value=f"{member.mention} (`{member}`)", inline=False)
        roles = [r.mention for r in member.roles if r != member.guild.default_role]
        if roles:
            embed.add_field(name="Roles at Departure", value=' '.join(roles), inline=False)
        timestamp_footer(embed)

        await self._send_log(member.guild.id, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """Log nickname changes to the log channel (level 3+).

        :param before: member state before the update
        :type before: discord.Member
        :param after: member state after the update
        :type after: discord.Member
        """
        if before.nick == after.nick:
            return

        config = self._get_config(before.guild.id)
        if config.level < 3:
            return

        embed = discord.Embed(title="Nickname Changed", colour=discord.Colour.blurple())
        embed.set_author(name=after.display_name, icon_url=after.display_avatar)
        embed.add_field(name="User", value=after.mention, inline=False)
        embed.add_field(name="Before", value=before.nick or "*none*", inline=True)
        embed.add_field(name="After", value=after.nick or "*none*", inline=True)
        timestamp_footer(embed)

        await self._send_log(before.guild.id, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        """Log member bans to the log channel (level 4+).

        :param guild: the guild the ban occurred in
        :type guild: discord.Guild
        :param user: the user who was banned
        :type user: discord.User
        """
        config = self._get_config(guild.id)
        if config.level < 4:
            return

        embed = discord.Embed(title="Member Banned", colour=discord.Colour.dark_red())
        embed.set_author(name=user.display_name, icon_url=user.display_avatar)
        embed.add_field(name="User", value=f"{user.mention} (`{user}`)", inline=False)
        timestamp_footer(embed)

        await self._send_log(guild.id, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        """Log member unbans to the log channel (level 4+).

        :param guild: the guild the unban occurred in
        :type guild: discord.Guild
        :param user: the user who was unbanned
        :type user: discord.User
        """
        config = self._get_config(guild.id)
        if config.level < 4:
            return

        embed = discord.Embed(title="Member Unbanned", colour=discord.Colour.green())
        embed.set_author(name=user.display_name, icon_url=user.display_avatar)
        embed.add_field(name="User", value=f"{user.mention} (`{user}`)", inline=False)
        timestamp_footer(embed)

        await self._send_log(guild.id, embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        """Log role creation to the log channel (level 4+).

        :param role: the role that was created
        :type role: discord.Role
        """
        config = self._get_config(role.guild.id)
        if config.level < 4:
            return

        embed = discord.Embed(title="Role Created", colour=role.colour)
        embed.add_field(name="Role", value=f"{role.mention} (`{role.name}`)", inline=False)
        timestamp_footer(embed)

        await self._send_log(role.guild.id, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        """Log role deletion to the log channel (level 4+).

        :param role: the role that was deleted
        :type role: discord.Role
        """
        config = self._get_config(role.guild.id)
        if config.level < 4:
            return

        embed = discord.Embed(title="Role Deleted", colour=discord.Colour.dark_grey())
        embed.add_field(name="Role", value=f"`{role.name}`", inline=False)
        timestamp_footer(embed)

        await self._send_log(role.guild.id, embed)


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Moderation(bot))
