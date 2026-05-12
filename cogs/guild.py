"""Guild-level status overview for all user-facing cogs."""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = ["Justin Panchula", "Claude"]
__version__ = "0.2.0"
__status__ = "Development"

# Standard library
from logging import getLogger

# Third-party
import discord
from discord.ext import commands
from discord import app_commands
from asyncpg.exceptions import PostgresError

# Internal
from start import CENBot
from utils.embeds import requester_footer, BRAND_COLOR

log = getLogger('CENBot.guild')

_MODERATION_LEVELS = {0: "Off", 1: "Reports", 2: "Messages", 3: "Members", 4: "Server"}


@app_commands.guild_only()
class Guild(commands.GroupCog, name="guild"):
    """Guild configuration status overview."""

    def __init__(self, bot: CENBot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(name="status", description="Show the configuration status of all bot modules")
    async def status(self, interaction: discord.Interaction) -> None:
        """Display the enabled state and settings for every user-facing cog.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                                          SELECT
                                              moderation_level,
                                              moderation_log_channel,
                                              moderation_report_channel,
                                              moderation_new_member_timeout,
                                              welcome_enabled,
                                              welcome_channel,
                                              welcome_message,
                                              twitch_enabled,
                                              twitch_alert_channel,
                                              twitch_alert_role,
                                              youtube_enabled,
                                              youtube_upload_alert_channel,
                                              youtube_live_alert_channel,
                                              youtube_alert_role,
                                              (SELECT COUNT(*) FROM cenbot.twitch_subscriptions WHERE guild_id=$1) AS twitch_sub_count,
                                              (SELECT COUNT(*) FROM cenbot.youtube_subscriptions WHERE guild_id=$1) AS youtube_sub_count
                                          FROM cenbot.guilds
                                          WHERE id=$1
                                          """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching guild settings, please try again.", ephemeral=True)
            return

        embed = discord.Embed(title="Guild Status", color=BRAND_COLOR)

        # Moderation
        mod_level = row['moderation_level'] if row else 0
        mod_log = row['moderation_log_channel'] if row else None
        mod_report = row['moderation_report_channel'] if row else None
        mod_timeout = row['moderation_new_member_timeout'] if row else 0
        embed.add_field(name="Moderation", value="\n".join([
            f"**Status:** {'Off' if mod_level == 0 else f'Level {mod_level} — {_MODERATION_LEVELS[mod_level]}'}",
            f"**Log channel:** {'<#' + str(mod_log) + '>' if mod_log else 'Not set'}",
            f"**Report channel:** {'<#' + str(mod_report) + '>' if mod_report else 'Not set'}",
            f"**New-member timeout:** {mod_timeout}s" if mod_timeout else "**New-member timeout:** Disabled",
        ]), inline=False)

        # Welcome
        welcome_enabled = row['welcome_enabled'] if row else False
        welcome_channel = row['welcome_channel'] if row else None
        welcome_msg = row['welcome_message'] if row else None
        if welcome_msg and len(welcome_msg) > 60:
            welcome_msg = welcome_msg[:57] + "…"
        embed.add_field(name="Welcome", value="\n".join([
            f"**Status:** {'Enabled' if welcome_enabled else 'Disabled'}",
            f"**Channel:** {'<#' + str(welcome_channel) + '>' if welcome_channel else 'Not configured'}",
            f"**Message:** \"{welcome_msg}\"" if welcome_msg else "**Message:** Not set",
        ]), inline=False)

        # Twitch
        twitch_enabled = row['twitch_enabled'] if row else False
        twitch_channel = row['twitch_alert_channel'] if row else None
        twitch_role = row['twitch_alert_role'] if row else None
        twitch_subs = row['twitch_sub_count'] if row else 0
        embed.add_field(name="Twitch", value="\n".join([
            f"**Status:** {'Enabled' if twitch_enabled else 'Disabled'}",
            f"**Alert channel:** {'<#' + str(twitch_channel) + '>' if twitch_channel else 'Not configured'}",
            f"**Alert role:** {'<@&' + str(twitch_role) + '>' if twitch_role else 'Not set'}",
            f"**Subscriptions:** {twitch_subs}",
        ]), inline=False)

        # YouTube
        yt_enabled = row['youtube_enabled'] if row else False
        yt_upload = row['youtube_upload_alert_channel'] if row else None
        yt_live = row['youtube_live_alert_channel'] if row else None
        yt_role = row['youtube_alert_role'] if row else None
        yt_subs = row['youtube_sub_count'] if row else 0
        embed.add_field(name="YouTube", value="\n".join([
            f"**Status:** {'Enabled' if yt_enabled else 'Disabled'}",
            f"**Upload channel:** {'<#' + str(yt_upload) + '>' if yt_upload else 'Not configured'}",
            f"**Live channel:** {'<#' + str(yt_live) + '>' if yt_live else 'Not configured'}",
            f"**Alert role:** {'<@&' + str(yt_role) + '>' if yt_role else 'Not set'}",
            f"**Subscriptions:** {yt_subs}",
        ]), inline=False)

        # Always-enabled cogs with no per-guild settings
        embed.add_field(name="XP", value="**Status:** Always enabled", inline=False)
        embed.add_field(name="Radio", value="**Status:** Always enabled", inline=False)
        embed.add_field(name="Utility", value="**Status:** Always enabled", inline=False)

        requester_footer(embed, interaction)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Guild(bot))
