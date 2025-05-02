__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Guild activity moderation"""

# Module imports
from modules.appcommand_checks import is_app_enabled

# Discord imports
from start import cenbot
import discord
from discord.ext import commands
from discord import app_commands

# Python imports
from datetime import timedelta
from typing import Literal

# Logging
from asyncpg.exceptions import PostgresError
from logging import getLogger
log = getLogger('CENBot.moderation')


@app_commands.guild_only()
@is_app_enabled()
class moderation(commands.GroupCog, name="moderation"):
    """More advanced moderation than Discord has built-in.
    """
    def __init__(self, bot: cenbot):
        self.bot = bot

        # Add context menus from this cog
        self.ctx_report_message = app_commands.ContextMenu(
            name="Report Messsage",
            callback=self.report_message
        )
        self.bot.tree.add_command(self.ctx_report_message)

        self.ctx_report_user = app_commands.ContextMenu(
            name="Report User",
            callback=self.report_user
        )
        self.bot.tree.add_command(self.ctx_report_user)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name="set_channel"
    )
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        """Sets the channel guild reports will be sent to.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param channel: the text channel to send guild reports to
        :type channel: discord.TextChannel
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.moderation (guild_id, mod_channel) VALUES ($1, $2) ON CONFLICT (guild_id) DO
                                   UPDATE SET mod_channel=$2 WHERE cenbot.moderation.guild_id=$1
                                   """, interaction.guild.id, channel.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Log channel set to ``{channel.category}: #{channel.name}``", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name="set_level"
    )
    async def set_level(self, interaction: discord.Interaction, level: Literal['0: None', '1: Default (Reports Only)', '2: Message Activity', '3: All Activity']) -> None:
        """Sets the level of reporting the bot will perform.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param level: the level of reporting
        :type level: Literal['0: None', '1: Default (Reports Only)', '2: Message Edits', '3: All Messages', '4: All Activity']
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.moderation (guild_id, mod_level) VALUES ($1, $2) ON CONFLICT (guild_id) DO
                                   UPDATE SET mod_level=$2 WHERE cenbot.moderation.guild_id=$1
                                   """, interaction.guild.id, int(level[0:1]))
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Moderation level set to ``{level}``.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command(
        name="set_new_member_message_timer"
    )
    async def set_new_member_message_timer(self, interaction: discord.Interaction, seconds: int) -> None:
        """Set the duration (in seconds) that new members will not be able to send messages for.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param seconds: the number of seconds to set the timer for
        :type seconds: int
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.moderation (guild_id, new_member_message_timer) VALUES ($1, $2) ON CONFLICT (guild_id) DO
                                   UPDATE SET mod_level=$2 WHERE cenbot.moderation.guild_id=$1
                                   """, interaction.guild.id, seconds)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Set new member message timer to ``{seconds} seconds``", ephemeral=True)

    async def report_message(self, interaction: discord.Interaction, msg: discord.Message) -> None:
        """Report a message to the moderation channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param msg: the message reported
        :type msg: discord.Message
        """
        # Defer response
        await interaction.response.defer(ephemeral=True)

        # Get data from database
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT cenbot.moderation.mod_level, cenbot.moderation.mod_channel, cenbot.guilds.moderation_enabled
                                             FROM cenbot.moderation INNER JOIN cenbot.guilds
                                                 ON (cenbot.moderation.guild_id=cenbot.guilds.guild_id)
                                             WHERE cenbot.guilds.guild_id=$1
                                             """, msg.guild.id)
        except Exception as e:
            log.exception(e)

        # Check for record
        if record:
            # Check if mod level is 1 or above
            if record['mod_level'] >= 1 and record['moderation_enabled'] is True:
                # Create embed
                embed = discord.Embed(colour=discord.Colour.pink())
                embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)
                embed.add_field(name='Reported Message', value=f"A message sent by {msg.author.mention} was reported in {msg.channel.mention}", inline=False)

                # Ignore impossible message
                try:
                    embed.add_field(name='Content', value=msg.content, inline=False)
                except Exception as e:
                    log.exception(e)
                    return
                else:
                    embed.set_footer(text=f"{discord.utils.utcnow().strftime('%d/%m/%y - %H:%M:%S')}")

                    # Send report to channel
                    await self.bot.get_channel(record['mod_channel']).send(content="@everyone", embed=embed)

                    # Respond
                    await interaction.followup.send("Message reported.")

    async def report_user(self, interaction: discord.Interaction, member: discord.Member) -> None:
        """Report a user to the moderation channel.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param msg: the message reported
        :type msg: discord.Message
        """
        # Defer response
        await interaction.response.defer(ephemeral=True)

        # Get data from database
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT cenbot.moderation.mod_level, cenbot.moderation.mod_channel, cenbot.guilds.moderation_enabled
                                             FROM cenbot.moderation INNER JOIN cenbot.guilds
                                                 ON (cenbot.moderation.guild_id=cenbot.guilds.guild_id)
                                             WHERE cenbot.guilds.guild_id=$1
                                             """, member.guild.id)
        except Exception as e:
            log.exception(e)

        # Check for record
        if record:
            # Check if mod level is 1 or above
            if record['mod_level'] >= 1 and record['moderation_enabled'] is True:
                # Create embed
                embed = discord.Embed(colour=discord.Colour.pink())
                embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)
                embed.add_field(name='Reported User', value=f"{member.mention} was reported in {interaction.channel.mention} by {interaction.user.mention}", inline=False)
                embed.set_footer(text=f"{discord.utils.utcnow().strftime('%d/%m/%y - %H:%M:%S')}")

                # Send report to channel
                await self.bot.get_channel(record['mod_channel']).send(content="@everyone", embed=embed)

                # Respond
                await interaction.followup.send("User reported.")

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        """Spam protection (level 1 and above)

        :param msg: the discord message
        :type msg: discord.Message
        """
        # Ignore messages from self or in private channels
        if self.bot.user == msg.author or msg.channel.type == discord.ChannelType.private:
            return

        # Get data from database
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT cenbot.moderation.mod_level, cenbot.moderation.mod_channel, cenbot.guilds.moderation_enabled, cenbot.moderation.new_member_message_timer
                                             FROM cenbot.moderation INNER JOIN cenbot.guilds
                                               ON (cenbot.moderation.guild_id=cenbot.guilds.guild_id)
                                             WHERE cenbot.guilds.guild_id=$1
                                             """, msg.guild.id)
        except Exception as e:
            log.exception(e)

        # Check for record
        if record:
            # Check if mod level is 1 or above
            if record['mod_level'] >= 1 and record['moderation_enabled'] is True:
                # Check if user is a member of the server for longer than the specified time
                if msg.author.joined_at + timedelta(seconds=record['new_member_message_timer']) >= discord.utils.utcnow():
                    # Delete message
                    await msg.delete()

                    # Send warning message to the user
                    await msg.author.send(f"Your message in ``{msg.guild.name}`` was deleted because you are not a member of the server for longer than ``{record['new_member_message_timer']} seconds``.")
        else:
            # Check if user is a member of the server for longer than the 120 seconds
            if msg.author.joined_at + timedelta(seconds=120) >= discord.utils.utcnow():
                # Delete message
                await msg.delete()

                # Send warning message to the user
                await msg.author.send(f"Your message in ``{msg.guild.name}`` was deleted because you are not a member of the server for longer than ``{120} seconds``.")

    @commands.Cog.listener()
    async def on_message_edit(self, msg_before: discord.Message, msg_after: discord.Message) -> None:
        """Edit message tracking (level 2 and above)

        :param msg_before: the original discord message
        :type msg_before: discord.Message
        :param msg_after: the edited discord message
        :type msg_after: discord.Message
        """
        # Ignore messages from self or in private channels
        if self.bot.user == msg_before.author:
            return

        # Get data from database
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT cenbot.moderation.mod_level, cenbot.moderation.mod_channel, cenbot.guilds.moderation_enabled
                                             FROM cenbot.moderation INNER JOIN cenbot.guilds
                                                 ON (cenbot.moderation.guild_id=cenbot.guilds.guild_id)
                                             WHERE cenbot.guilds.guild_id=$1
                                             """, msg_before.guild.id)
        except Exception as e:
            log.exception(e)

        # Check for record
        if record:
            # Check if mod level is 2 or above
            if record['mod_level'] >= 2 and record['moderation_enabled'] is True:
                # Build embed
                embed = discord.Embed(colour=discord.Colour.yellow())
                embed.set_author(name=msg_before.author.display_name, icon_url=msg_before.author.display_avatar)
                embed.add_field(name='Message Alert: Edit', value=f"A message sent by {msg_before.author.mention} was edited in {msg_before.channel.mention} \
                                                                    \n[View Message]({msg_after.jump_url})", inline=False)
                # Ignore impossible messages
                try:
                    embed.add_field(name='Before', value=msg_before.content, inline=False)
                except Exception as e:
                    log.exception(e)
                    return
                else:
                    embed.add_field(name='After', value=msg_after.content, inline=False)

                # Set footer
                embed.set_footer(text=f"{discord.utils.utcnow().strftime('%d/%m/%y - %H:%M:%S')}")

                # Send to channel
                await self.bot.get_channel(record['mod_channel']).send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message) -> None:
        """Deleted message tracking (level 2 and above)

        :param msg: the deleted discord message
        :type msg: discord.Message
        """
        # Ignore messages from self or in private channels
        if self.bot.user == msg.author:
            return

        # Get data from database
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT cenbot.moderation.mod_level, cenbot.moderation.mod_channel, cenbot.guilds.moderation_enabled
                                             FROM cenbot.moderation INNER JOIN cenbot.guilds
                                                 ON (cenbot.moderation.guild_id=cenbot.guilds.guild_id)
                                             WHERE cenbot.guilds.guild_id=$1
                                             """, msg.guild.id)
        except Exception as e:
            log.exception(e)

        # Check for record
        if record:
            # Check if mod level is 2 or above
            if record['mod_level'] >= 2 and record['moderation_enabled'] is True:
                # Build embed
                embed = discord.Embed(colour=discord.Colour.orange())
                embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar)
                embed.add_field(name='Message Alert: Delete', value=f"A message sent by {msg.author.mention} was edited in {msg.channel.mention} \
                                                                    \n[View Message]({msg.jump_url})", inline=False)
                # Ignore impossible messages
                try:
                    embed.add_field(name='Content', value=msg.content)
                except Exception as e:
                    log.exception(e)
                    return

                # Set footer
                embed.set_footer(text=f"{discord.utils.utcnow().strftime('%d/%m/%y - %H:%M:%S')}")

                # Send to channel
                await self.bot.get_channel(record['mod_channel']).send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        """Voice state tracking (level 3 and above)

        :param member: the guild member who's voice state changed
        :type member: discord.Member
        :param before: the state before
        :type before: discord.VoiceState
        :param after: the state after
        :type after: discord.VoiceState
        """
        # Ignore messages from self or in private channels
        if self.bot.user.id == member.id:
            return

        # Get data from database
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT cenbot.moderation.mod_level, cenbot.moderation.mod_channel, cenbot.guilds.moderation_enabled
                                             FROM cenbot.moderation INNER JOIN cenbot.guilds
                                                 ON (cenbot.moderation.guild_id=cenbot.guilds.guild_id)
                                             WHERE cenbot.guilds.guild_id=$1
                                             """, member.guild.id)
        except Exception as e:
            log.exception(e)

        # Check for record
        if record:
            # Check if mod level is 3 or above
            if record['mod_level'] >= 3 and record['moderation_enabled'] is True:
                # Check if the user joined or left a voice channel
                if before.channel is None:
                    # Build embed
                    embed = discord.Embed(colour=discord.Colour.green())
                    embed.set_author(name=member.display_name, icon_url=member.display_avatar)
                    embed.add_field(name='Voice Alert', value=f"{member.mention} has joined {after.channel.mention}", inline=False)
                elif after.channel is None:
                    # Build embed
                    embed = discord.Embed(colour=discord.Colour.red())
                    embed.set_author(name=member.display_name, icon_url=member.display_avatar)
                    embed.add_field(name='Voice Alert', value=f"{member.mention} has left {before.channel.mention}", inline=False)
                else:
                    # Build embed
                    embed = discord.Embed(colour=discord.Colour.yellow())
                    embed.set_author(name=member.display_name, icon_url=member.display_avatar)
                    embed.add_field(name='Voice Alert', value=f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}", inline=False)

                # Set footer
                embed.set_footer(text=f"{discord.utils.utcnow().strftime('%d/%m/%y - %H:%M:%S')}")

                # Send to channel
                await self.bot.get_channel(record['mod_channel']).send(embed=embed)


# Add to bot
async def setup(bot: cenbot) -> None:
    await bot.add_cog(moderation(bot))