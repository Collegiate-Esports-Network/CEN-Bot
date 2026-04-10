"""Guild management"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"

# Standard library
from logging import getLogger

# Third-party
import discord
from discord.ext import commands
from discord import app_commands

# Internal
from start import CENBot

log = getLogger('CENBot.guilds')


@app_commands.guild_only()
class Guilds(commands.GroupCog, name="guild"):
    """Guild management functions."""
    def __init__(self, bot: CENBot):
        self.bot = bot
        super().__init__()

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command()
    async def setup(self, interaction: discord.Interaction) -> None:
        """Does initial server setup

        :param interaction: the discord interaction.
        :type interaction: discord.Interaction
        """
        await interaction.response.defer(ephemeral=True)

        # Check for CENBot Admin role
        role = discord.utils.get(interaction.guild.roles, name="CENBot Admin")

        # Create bot-manager role if it doesn't exist
        if role is None:
            try:
                role = await interaction.guild.create_role(name="CENBot Admin", color=0x2374A5, permissions=discord.Permissions(administrator=True), reason="``CENBot Admin`` role created by CEN Bot.")
            except discord.Forbidden:
                log.warning(f"CENBot Admin role creation for guild {interaction.guild.id}: {interaction.guild.name} is forbidden")
                await interaction.guild.owner.send("CENBot Admin role creation is not possible as the bot does not have the proper permissions. Please give the CEN Bot administrator permissions, and try again.")
                return
            except Exception as e:
                log.exception(e)
                await interaction.guild.owner.send("CENBot Admin role creation is not possible at the moment. Please try again.")
                return

        # Give role to interaction user
        await interaction.user.add_roles(role)

        # Validate guild_id in Supabase
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT FROM cenbot.guilds
                                             WHERE guild_id=$1
                                             """, interaction.guild.id)
        except Exception as e:
            log.exception(e)
            await interaction.guild.owner.send("The CENBot was unable to validate the server. Please try again.")
            return

        if not record:
            try:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute("""
                                       INSERT INTO cenbot.guilds (guild_id)
                                       VALUES ($1)
                                       ON CONFLICT DO NOTHING
                                       """, interaction.guild.id)
            except Exception as e:
                log.exception(e)
                await interaction.guild.owner.send("The CENBot was unable to validate the server. Please try again.")
                return

        await interaction.followup.send("The server has been set up.")

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def module_status(self, interaction: discord.Interaction) -> None:
        """Checks the status of modules.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT *
                                             FROM cenbot.guilds
                                             WHERE guild_id=$1
                                             """, interaction.guild.id)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("The CENBot was unable to check the status of modules. Please try again.", ephemeral=True)
            return

        if record:
            logging = ("Enabled", self.bot.get_channel(record['logging_channel']).mention) if record['logging_channel'] else ("Disabled", "None")
            reporting = ("Enabled", self.bot.get_channel(record['reporting_channel']).mention) if record['reporting_channel'] else ("Disabled", "None")
            twitch = ("Enabled", self.bot.get_channel(record['twitch_alert_channel']).mention) if record['twitch_alert_channel'] else ("Disabled", "None")
            welcome = ("Enabled", self.bot.get_channel(record['welcome_channel']).mention) if record['welcome_channel'] else ("Disabled", "None")
            youtube = ("Enabled", self.bot.get_channel(record['youtube_alert_channel']).mention) if record['youtube_alert_channel'] else ("Disabled", "None")

            embed = discord.Embed(title="Module Info", description="Here is the status of all bot modules in this guild.", colour=0x2374A5)
            embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
            embed.add_field(name="Logging", value=f"{logging[0]} | {logging[1]}", inline=False)
            embed.add_field(name="Reporting", value=f"{reporting[0]} | {reporting[1]}", inline=False)
            embed.add_field(name="Twitch", value=f"{twitch[0]} | {twitch[1]}", inline=False)
            embed.add_field(name="Welcome", value=f"{welcome[0]} | {welcome[1]}", inline=False)
            embed.add_field(name="YouTube", value=f"{youtube[0]} | {youtube[1]}", inline=False)
            embed.set_footer(text=f"{discord.utils.utcnow().strftime('%d/%m/%y - %H:%M:%S')}")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("The CENBot was unable to check the status of modules. Please try again.", ephemeral=True)


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Guilds(bot))