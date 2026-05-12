"""Player profile and registration commands."""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = ["Justin Panchula", "Claude"]
__version__ = "0.2.0"
__status__ = "Development"

# Standard library
import secrets
from logging import getLogger
from urllib.parse import urlencode

# Third-party
import discord
from discord.ext import commands
from discord import app_commands
from asyncpg.exceptions import PostgresError

# Internal
from start import CENBot
from utils.embeds import requester_footer, BRAND_COLOR

log = getLogger('CENBot.profiles')

# Window the bot will tell users their link is good for; must match
# `pending_registrations.expires_at` default in the migration.
LINK_TTL_MINUTES = 10


@app_commands.guild_only()
class Profile(commands.GroupCog, name='profile'):
    """Commands for CEN player profiles, linked game accounts, and registration."""

    def __init__(self, bot: CENBot) -> None:
        self.bot = bot
        super().__init__()

    ### Registration ###

    @app_commands.command(name='register', description="Link your Discord account to CEN.")
    async def profile_register(self, interaction: discord.Interaction) -> None:
        """Initiate the bot-driven OAuth flow.

        Validates that the invoker is not already linked, persists a
        ``pending_registrations`` row keyed by a fresh CSRF state token, DMs
        the OAuth login URL, and subscribes via realtime so the bot can DM a
        confirmation when the web callback flips ``completed``.

        :param interaction: the discord interaction that triggered the command
        :type interaction: discord.Interaction
        """
        # Defer ephemerally; downstream DB + DM work may exceed the 3s ack window
        await interaction.response.defer(ephemeral=True)

        discord_id = interaction.user.id
        username = str(interaction.user)

        ### Short-circuit: already registered ###
        try:
            async with self.bot.db_pool.acquire() as conn:
                existing = await conn.fetchval(
                    "SELECT user_id FROM public.profiles WHERE discord_id = $1",
                    discord_id,
                )
        except PostgresError as e:
            log.exception(e)
            await interaction.followup.send(
                "There was an error checking your registration, please try again.",
                ephemeral=True,
            )
            return

        if existing is not None:
            await interaction.followup.send(
                "You're already linked to a CEN profile. "
                "Visit https://collegiateesportsnetwork.org/account to manage it.",
                ephemeral=True,
            )
            return

        ### Persist a pending registration keyed by a fresh CSRF state token ###
        state = secrets.token_urlsafe(32)
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO public.pending_registrations (state, discord_id, username)
                    VALUES ($1, $2, $3)
                    """,
                    state, discord_id, username,
                )
        except PostgresError as e:
            log.exception(e)
            await interaction.followup.send(
                "There was an error starting registration, please try again.",
                ephemeral=True,
            )
            return

        ### Subscribe to the realtime completion event before sending the URL ###
        try:
            await self.bot.realtime.watch(discord_id, self._notify_complete)
        except Exception as e:
            # Subscription failure is non-fatal — web flow still succeeds, the user
            # just won't get a DM confirmation. Keep the command flow moving.
            log.exception(e)

        ### Build the OAuth URL and DM (or fall back to ephemeral) ###
        params = urlencode({"source": "bot", "state": state})
        url = f"{self.bot.web_base_url}/api/v1/auth/discord/login?{params}"

        try:
            await interaction.user.send(
                "Click the link below to link your Discord account to CEN. "
                f"This link expires in **{LINK_TTL_MINUTES} minutes**.\n\n{url}"
            )
        except discord.Forbidden:
            # User has DMs closed for non-friends; deliver the link ephemerally instead
            await interaction.followup.send(
                "I can't DM you, so here's your registration link "
                f"(only you can see this, expires in **{LINK_TTL_MINUTES} minutes**):\n{url}",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "Check your DMs for a registration link.",
            ephemeral=True,
        )
        log.info(f"registration: handoff started for discord_id={discord_id}")

    async def _notify_complete(self, discord_id: int) -> None:
        """Realtime completion handler: DM the user a confirmation message.

        Looked up via the bot's user cache; falls back to a fetch when the user
        isn't cached. Failures are logged but never raised — registration
        already succeeded on the web side.

        :param discord_id: Discord snowflake of the user who finished registering
        :type discord_id: int
        """
        user = self.bot.get_user(discord_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(discord_id)
            except discord.HTTPException as e:
                log.exception(e)
                return

        try:
            await user.send("You're registered! Welcome to the CEN.")
        except discord.Forbidden:
            log.warning(f"registration: cannot DM completion to discord_id={discord_id} (DMs closed)")
        except discord.HTTPException as e:
            log.exception(e)

        log.info(f"registration: handoff complete for discord_id={discord_id}")

    ### Profile ###

    @app_commands.command(name='view', description="View your CEN profile and game stats.")
    async def profile_view(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        """Display a CEN profile embed.

        Without a member argument (or when the member is the invoker), shows the
        full profile: personal details, XP, and per-game ranked stats. When a
        different member is provided, only their linked game account IDs are shown —
        no personal fields are exposed.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param member: the member to look up; defaults to the invoker
        :type member: discord.Member | None
        """
        ### Self view ###
        if member is None or member == interaction.user:
            try:
                async with self.bot.db_pool.acquire() as con:
                    record = await con.fetchrow("""
                        SELECT
                            p.steam_id, p.battlenet_id, p.riot_id, p.riot_region, p.r6_username,
                            p.school, p.pronouns, p.graduation_year, p.major, p.message_xp,
                            cs.premier_rank, cs.faceit_rank, cs.faceit_elo, cs.game_name,
                            l.solo_tier, l.solo_rank, l.solo_lp,
                            l.flex_tier, l.flex_rank, l.flex_lp,
                            v.current_tier, v.current_rr, v.peak_tier,
                            o.tank_division, o.damage_division, o.support_division,
                            o.open_division, o.season,
                            r.ranked_tier, r.ranked_mmr
                        FROM public.profiles p
                        LEFT JOIN public.cs_stats  cs ON cs.steam_id    = p.steam_id
                        LEFT JOIN public.lol_stats l  ON l.riot_id      = p.riot_id
                        LEFT JOIN public.val_stats v  ON v.riot_id      = p.riot_id
                        LEFT JOIN public.ow_stats  o  ON o.battlenet_id = p.battlenet_id
                        LEFT JOIN public.r6_stats  r  ON r.r6_username  = p.r6_username
                        WHERE p.discord_id = $1
                    """, interaction.user.id)
            except PostgresError as e:
                log.exception(e)
                await interaction.response.send_message("There was an error fetching your profile, please try again.", ephemeral=True)
                return

            if record is None:
                await interaction.response.send_message(
                    "You don't have a CEN profile linked to your Discord account. "
                    "You can create one with `/profile register`.",
                    ephemeral=True,
                )
                return

            user = interaction.user
            embed = discord.Embed(color=BRAND_COLOR)
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

            # About — personal details
            about_lines = []
            if record['school']:
                about_lines.append(f"**School:** {record['school']}")
            if record['pronouns']:
                about_lines.append(f"**Pronouns:** {record['pronouns']}")
            if record['graduation_year']:
                about_lines.append(f"**Class of:** {record['graduation_year']}")
            if record['major']:
                about_lines.append(f"**Major:** {record['major']}")
            if about_lines:
                embed.add_field(name="About", value="\n".join(about_lines), inline=False)

            # XP
            if record['message_xp'] is not None:
                embed.add_field(name="XP", value=str(record['message_xp']), inline=False)

            # CS2
            if record['steam_id']:
                cs_lines = []
                if record['game_name']:
                    cs_lines.append(f"**Account:** {record['game_name']}")
                if record['premier_rank'] is not None:
                    cs_lines.append(f"**Premier:** {record['premier_rank']}")
                if record['faceit_rank'] is not None:
                    faceit = f"**FACEIT:** Level {record['faceit_rank']}"
                    if record['faceit_elo'] is not None:
                        faceit += f" ({record['faceit_elo']} ELO)"
                    cs_lines.append(faceit)
                # Fall back to raw Steam ID if no stats have been synced yet
                if not cs_lines:
                    cs_lines.append(record['steam_id'])
                embed.add_field(name="CS2", value="\n".join(cs_lines), inline=True)

            # League of Legends — riot_id must be set and at least one rank present
            if record['riot_id'] and (record['solo_tier'] or record['flex_tier']):
                lol_lines = []
                if record['solo_tier']:
                    solo = f"**Solo/Duo:** {record['solo_tier']} {record['solo_rank'] or ''}".strip()
                    if record['solo_lp'] is not None:
                        solo += f" — {record['solo_lp']} LP"
                    lol_lines.append(solo)
                if record['flex_tier']:
                    flex = f"**Flex:** {record['flex_tier']} {record['flex_rank'] or ''}".strip()
                    if record['flex_lp'] is not None:
                        flex += f" — {record['flex_lp']} LP"
                    lol_lines.append(flex)
                embed.add_field(name="League of Legends", value="\n".join(lol_lines), inline=True)

            # Valorant — riot_id must be set and current tier present
            if record['riot_id'] and record['current_tier']:
                val_lines = []
                curr = f"**Current:** {record['current_tier']}"
                if record['current_rr'] is not None:
                    curr += f" — {record['current_rr']} RR"
                val_lines.append(curr)
                if record['peak_tier']:
                    val_lines.append(f"**Peak:** {record['peak_tier']}")
                embed.add_field(name="Valorant", value="\n".join(val_lines), inline=True)

            # Overwatch 2
            if record['battlenet_id'] and any(record[k] for k in ('tank_division', 'damage_division', 'support_division', 'open_division')):
                ow_lines = []
                if record['tank_division']:
                    ow_lines.append(f"**Tank:** {record['tank_division']}")
                if record['damage_division']:
                    ow_lines.append(f"**Damage:** {record['damage_division']}")
                if record['support_division']:
                    ow_lines.append(f"**Support:** {record['support_division']}")
                if record['open_division']:
                    ow_lines.append(f"**Open:** {record['open_division']}")
                if record['season'] is not None:
                    ow_lines.append(f"*(Season {record['season']})*")
                embed.add_field(name="Overwatch 2", value="\n".join(ow_lines), inline=True)

            # Rainbow Six Siege
            if record['r6_username'] and record['ranked_tier']:
                r6 = f"**Rank:** {record['ranked_tier']}"
                if record['ranked_mmr'] is not None:
                    r6 += f" — {record['ranked_mmr']} MMR"
                embed.add_field(name="Rainbow Six Siege", value=r6, inline=True)

            requester_footer(embed, interaction)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        ### Other-user lookup — game IDs only, no personal fields ###
        try:
            async with self.bot.db_pool.acquire() as con:
                record = await con.fetchrow("""
                    SELECT steam_id, battlenet_id, riot_id, riot_region, r6_username
                    FROM public.profiles
                    WHERE discord_id = $1
                """, member.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching that profile, please try again.", ephemeral=True)
            return

        embed = discord.Embed(title=f"{member.display_name}'s Game IDs", color=BRAND_COLOR)

        if record is None or not any(record[k] for k in ('steam_id', 'battlenet_id', 'riot_id', 'r6_username')):
            embed.add_field(name="", value="No linked game accounts.", inline=False)
        else:
            if record['steam_id']:
                embed.add_field(name="CS2", value=record['steam_id'], inline=True)
            if record['battlenet_id']:
                embed.add_field(name="Battle.net", value=record['battlenet_id'], inline=True)
            if record['riot_id']:
                riot = record['riot_id']
                if record['riot_region']:
                    riot += f" [{record['riot_region'].upper()}]"
                embed.add_field(name="Riot (LoL / Valorant)", value=riot, inline=True)
            if record['r6_username']:
                embed.add_field(name="Rainbow Six Siege", value=record['r6_username'], inline=True)

        requester_footer(embed, interaction)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Profile(bot))
