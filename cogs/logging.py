__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "3"
__status__ = "Production"
__doc__ = """Logs activity in discord servers"""

# Python imports
from datetime import datetime
from http.client import HTTPException
from typing import Literal

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
from logging import getLogger
from asyncpg.exceptions import PostgresError
log = getLogger('CENBot.logging')


@app_commands.guild_only()
class logging(commands.GroupCog, name='logging'):
    """These are all the logging functions.
    """
    def __init__(self, bot: cbot):
        self.bot = bot
        super().__init__()

    # Set log channel
    @app_commands.command(
        name='setlogchannel',
        description="Sets the channel server logs will be sent to."
    )
    @commands.has_role('bot manager')
    async def log_setlogchannel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE serverdata SET log_channel=$2 WHERE guild_id=$1", interaction.guild.id, channel.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Log channel set.", ephemeral=False)

    # Set report channel
    @app_commands.command(
        name='setreportchannel',
        description="Sets the channel server reports will be sent to."
    )
    @commands.has_role('bot manager')
    async def log_setreportchannel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE serverdata SET report_channel=$2 WHERE guild_id=$1", interaction.guild.id, channel.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Log channel set.", ephemeral=False)

    # Set log level
    @app_commands.command(
        name='setlevel',
        description="Sets the level server logs will track."
    )
    @commands.has_role('bot manager')
    async def log_setlevel(self, interaction: discord.Interaction,
                           level: Literal['0: None', '1: Default (Reports Only)', '2: Message Edits', '3: All Messages', '4: All Activity']) -> None:
        # Convert data
        level = int(level[0:1])
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE serverdata SET log_level=$2 WHERE guild_id=$1", interaction.guild.id, level)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Log level set.", ephemeral=False)

    # Log message edits (level 2)
    @commands.Cog.listener()
    async def on_message_edit(self, ctx_bef: discord.Message, ctx_aft: discord.Message) -> None:
        # Check null case
        if ctx_bef.guild is None or ctx_aft.guild is None or ctx_bef.guild.id is None or ctx_aft.guild.id is None:
            return

        # Check if bot sent message
        if ctx_bef.author.id == self.bot.user.id:
            return

        # Get log channel
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT log_channel FROM serverdata WHERE guild_id=$1", ctx_bef.guild.id)
            channel = response[0]['log_channel']
        except PostgresError as e:
            log.exception(e)
            return
        except AttributeError as e:
            log.exception(e)
            return

        # Get log level
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT log_level FROM serverdata WHERE guild_id=$1", ctx_bef.guild.id)
            level = response[0]['log_level']
        except PostgresError as e:
            log.exception(e)
            return
        except AttributeError as e:
            log.exception(e)
            return

        # Check log level
        if level < 2:
            return

        # Edited message embed
        embed = discord.Embed(colour=discord.Colour.gold())
        embed.set_author(name=ctx_bef.author.display_name, icon_url=ctx_bef.author.display_avatar)
        embed.add_field(name='Message Alert: Edit', value=f"A message sent by {ctx_bef.author.mention} was edited in {ctx_bef.channel.mention} \
                                                            \n[View Message]({ctx_aft.jump_url})", inline=False)
        # Ignore impossible message
        try:
            embed.add_field(name='Before', value=ctx_bef.content, inline=False)
        except discord.errors.HTTPException as e:
            log.exception(e)
            return
        except HTTPException as e:
            log.exception(e)
            return
        else:
            embed.add_field(name='After', value=ctx_aft.content, inline=False)
            embed.set_footer(text=f"{datetime.now().strftime('%d/%m/%y - %H:%M:%S')}")

        # Send to channel
        await self.bot.get_channel(channel).send(embed=embed)

    # Log message deletions (level 2)
    @commands.Cog.listener()
    async def on_message_delete(self, ctx: discord.Message) -> None:
        # Check null case
        if ctx.guild is None or ctx.guild.id is None:
            return

        # Check if bot sent message
        if ctx.author.id == self.bot.user.id:
            return

        # Get log channel
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT log_channel FROM serverdata WHERE guild_id=$1", ctx.guild.id)
            channel = response[0]['log_channel']
        except PostgresError as e:
            log.exception(e)
            return
        except AttributeError as e:
            log.exception(e)
            return

        # Get log level
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT log_level FROM serverdata WHERE guild_id=$1", ctx.guild.id)
            level = response[0]['log_level']
        except PostgresError as e:
            log.exception(e)
            return
        except AttributeError as e:
            log.exception(e)
            level = 0

        # Check log level
        if level < 2:
            return

        # Deleted message embed
        embed = discord.Embed(colour=discord.Colour.orange())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.add_field(name='Message Alert: Deletion', value=f"A message sent by {ctx.author.mention} was deleted in {ctx.channel.mention}", inline=False)
        # Ignore impossible message
        try:
            embed.add_field(name='Content', value=ctx.content)
        except discord.errors.HTTPException as e:
            log.exception(e)
            return
        except HTTPException as e:
            log.exception(e)
            return
        embed.set_footer(text=f'{datetime.now().strftime("%d/%m/%y - %H:%M:%S")}')

        # Send to channel
        await self.bot.get_channel(channel).send(embed=embed)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(logging(bot))

# # Context menu message reporting (Level 1 logging)
# @bot.tree.context_menu(
#     name='Report Message',
# )
# async def log_reportmessage(interaction: discord.Interaction, message: discord.Message) -> None:
#     # Defer response
#     await interaction.response.defer(ephemeral=True)

#     # Get log channel
#     try:
#         async with bot.db_pool.acquire() as con:
#             response = await con.fetch("SELECT report_channel FROM serverdata WHERE guild_id=$1", interaction.guild.id)
#         channel = response[0]['report_channel']
#     except PostgresError as e:
#         log.exception(e)
#         return
#     except AttributeError as e:
#         log.exception(e)
#         return

#     # Get log level
#     try:
#         async with bot.db_pool.acquire() as con:
#             response = await con.fetch("SELECT log_level FROM serverdata WHERE guild_id=$1", interaction.guild.id)
#         level = response[0]['log_level']
#     except PostgresError as e:
#         log.exception(e)
#         return
#     except AttributeError as e:
#         log.exception(e)
#         return

#     # Check log level
#     if level < 1:
#         return

#     # Reported message embed
#     embed = discord.Embed(colour=discord.Colour.red())
#     embed.set_author(name=message.author.name, icon_url=message.author.display_avatar)
#     embed.add_field(name='Reported Message', value=f"A message sent by {message.author.mention} was reported in {message.channel.mention}", inline=False)

#     # Ignore impossible message
#     try:
#         embed.add_field(name='Content', value=message.content, inline=False)
#     except discord.errors.HTTPException as e:
#         log.exception(e)
#         return
#     except HTTPException as e:
#         log.exception(e)
#         return
#     else:
#         embed.set_footer(text=f"{datetime.now().strftime('%d/%m/%y - %H:%M:%S')}")

#     # Send to channel
#     await bot.get_channel(channel).send(embed=embed)

#     # Respond
#     await interaction.followup.send("Message reported.")