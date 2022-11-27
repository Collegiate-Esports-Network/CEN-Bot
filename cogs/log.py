__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
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
import logging
from asyncpg.exceptions import PostgresError
logger = logging.getLogger('log')


class log(commands.GroupCog, name='log'):
    """These are all the logging functions
    """
    def __init__(self, bot: cbot):
        self.bot = bot
        super().__init__()

    # Set log channel
    @app_commands.command(
        name='setchannel',
        description="Sets the channel server logs will be sent to"
    )
    @commands.has_role('bot manager')
    async def log_setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            async with self.bot.pool.acquire() as con:
                await con.execute("UPDATE serverdata SET log_channel=$2 WHERE guild_id=$1", interaction.guild.id, channel.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Log channel set.", ephemeral=True)

    # Set log level
    @app_commands.command(
        name='setlevel',
        description="Sets the level server logs will track"
    )
    @commands.has_role('bot manager')
    async def log_setlevel(self, interaction: discord.Interaction,
                           level: Literal['0: None', '1: Default', '2: All Messages', '3: All Voice Activity', '4: All Activity']) -> None:
        try:
            async with self.bot.pool.acquire() as con:
                await con.execute("UPDATE serverdata SET log_level=$2 WHERE guild_id=$1", interaction.guild.id, level)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Log level set.", ephemeral=True)

    # Log message edits (level 1)
    @commands.Cog.listener()
    async def on_message_edit(self, ctx_bef: discord.Message, ctx_aft: discord.Message) -> None:
        # Get log channel
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("SELECT log_channel FROM serverdata WHERE guild_id=$1", ctx_bef.guild.id)
            channel = response[0]['log_channel']
        except PostgresError as e:
            logger.exception(e)
            return
        except AttributeError as e:
            logger.exception(e)
            return

        # Get log level
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("SELECT log_level FROM serverdata WHERE guild_id=$1", ctx_bef.guild.id)
            level = response[0]['log_level']
        except PostgresError as e:
            logger.exception(e)
            return
        except AttributeError as e:
            logger.exception(e)
            return

        # Check log level
        if level < 1:
            return

        # Edited message embed
        embed = discord.Embed(colour=discord.Colour.gold())
        embed.set_author(name=ctx_bef.author.display_name, icon_url=ctx_bef.author.display_avatar)
        embed.add_field(name='Message Alert: Edit', value=f"A message sent by {ctx_bef.author.mention} \
                                                            was edited in {ctx_bef.channel.mention} \
                                                            \n[View Message]({ctx_aft.jump_url})", inline=False)
        # Ignore impossible message
        try:
            embed.add_field(name='Before', value=ctx_bef.content, inline=False)
        except discord.errors.HTTPException as e:
            logger.exception(e)
            return
        except HTTPException as e:
            logger.exception(e)
            return
        else:
            embed.add_field(name='After', value=ctx_aft.content, inline=False)
            embed.set_footer(text=f"{datetime.now().strftime('%d/%m/%y - %H:%M:%S')}")

        # Send to channel
        await self.bot.get_channel(channel).send(embed=embed)

    # Log message deletions (level 1)
    @commands.Cog.listener()
    async def on_message_delete(self, ctx: discord.Message) -> None:
        # Get log channel
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("SELECT log_channel FROM serverdata WHERE guild_id=$1", ctx.guild.id)
            channel = response[0]['log_channel']
        except PostgresError as e:
            logger.exception(e)
            return
        except AttributeError as e:
            logger.exception(e)
            return

        # Get log level
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("SELECT log_level FROM serverdata WHERE guild_id=$1", ctx.guild.id)
            level = response[0]['log_level']
        except PostgresError as e:
            logger.exception(e)
            return
        except AttributeError as e:
            logger.exception(e)
            level = 0

        # Check log level
        if level < 1:
            return

        # Deleted message embed
        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.add_field(name='Message Alert: Deletion', value=f'A message sent by {ctx.author.mention} was deleted in {ctx.channel.mention}', inline=False)
        # Ignore impossible message
        try:
            embed.add_field(name='Content', value=ctx.content)
        except discord.errors.HTTPException as e:
            logger.exception(e)
            return
        except HTTPException as e:
            logger.exception(e)
            return
        embed.set_footer(text=f'{datetime.now().strftime("%d/%m/%y - %H:%M:%S")}')

        # Send to channel
        await self.bot.get_channel(channel).send(embed=embed)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(log(bot))