__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Guild management"""

# Discord imports
from start import cenbot
import discord
from discord.ext import commands
from discord import app_commands

# Typing
from typing import Literal

# Logging
from asyncpg.exceptions import PostgresError
from logging import getLogger
log = getLogger('CENBot.guilds')


@app_commands.guild_only()
class guilds(commands.GroupCog, name="guild"):
    """Guild management functions.
    """
    def __init__(self, bot: cenbot):
        self.bot = bot

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(
        name="setup"
    )
    async def setup(self, interaction: discord.Interaction) -> None:
        """Does initial server setup

        :param interaction: the discord interaction.
        :type interaction: discord.Interaction
        """
        # Defer
        await interaction.response.defer(ephemeral=True)

        # Create bot-manager role
        try:
            role = await interaction.guild.create_role(name="CENBot Admin", color=0x2374A5, permissions=discord.Permissions(administrator=True), reason="CENBot Admin role created by default.")
        except discord.Forbidden:
            log.warning(f"CENBot Admin role creation for guild {interaction.guild.id}: {interaction.guild.name} is forbidden")
            await interaction.guild.owner.send("CENBot Admin role creation is not possible as the bot does not have the proper permissions. Please create a role with the name ``CENBot Admin`` and give it, and the CEN Bot, administrator permissions.")
        except Exception as e:
            log.exception(e)
            await interaction.guild.owner.send("CENBot Admin role creation is not possible at the momement. Please create a role with the name ``CENBot Admin`` and give it administrator permissions.")

        # Give role to interaction user
        await interaction.user.add_roles(role)

        # Confirm
        await interaction.followup.send("The server has been set up.")

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name="toggle"
    )
    async def toggle(self, interaction: discord.Interaction, state: Literal["enable", "disable"], module: Literal["moderation", "roles", "voice", "welcome"]) -> None:
        """Toggles a module for this server

        :param interaction: the discord interaction.
        :type interaction: discord.Interaction
        :param module: the module to enable.
        :type module: Literal[&quot;moderation&quot;, &quot;roles&quot;, &quot;voice&quot;, &quot;welcome&quot;]
        """
        # Parse input
        if state == "enable":
            status = True
        else:
            status = False

        # Toggle modules
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Switch on module
                match module:
                    case "moderation":
                        await conn.execute("UPDATE cenbot.guilds SET moderation_enabled=$1 WHERE guild_id=$2", status, interaction.guild.id)
                    case "roles":
                        await conn.execute("UPDATE cenbot.guilds SET roles_enabled=$1 WHERE guild_id=$2", status, interaction.guild.id)
                    case "voice":
                        await conn.execute("UPDATE cenbot.guilds SET voice_enabled=$1 WHERE guild_id=$2", status, interaction.guild.id)
                    case "welcome":
                        await conn.execute("UPDATE cenbot.guilds SET welcome_enabled=$1 WHERE guild_id=$2", status, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message(f"There was an error enabling ``{module}``, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Moderation {state}d.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name="module_status"
    )
    async def module_status(self, interaction: discord.Interaction) -> None:
        """Checks module statuses for this server

        :param interaction: the discord interaction.
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("SELECT * FROM cenbot.guilds WHERE guild_id=$1", interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error getting your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            # Check for record
            if record:
                # Build embed
                embed = discord.Embed(title="Enabled Modules", color=0x2374A5)
                embed.set_author(name="CENBot", icon_url=self.bot.user.avatar.url)
                embed.add_field(name="Moderation", value=record['moderation_enabled'], inline=False)
                embed.add_field(name="Roles", value=record['roles_enabled'], inline=False)
                embed.add_field(name="Voice", value=record['voice_enabled'], inline=False)
                embed.add_field(name="Welcome", value=record['welcome_enabled'], inline=False)

                # Send embed
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                log.exception(f"Error retrieving module status for {interaction.guild.id}")
                await interaction.response.send_message("There was an error getting your data, please try again.", ephemeral=True)


# Add to bot
async def setup(bot: cenbot) -> None:
    await bot.add_cog(guilds(bot))