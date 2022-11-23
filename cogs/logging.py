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
import discord
from discord.ext import commands
from discord import app_commands

# Custom imports
from helper.get_id import get_id


class logging(commands.GroupCog, name='logging'):
    """These are all the logging functions
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    # Log message edits (level 1)
    @commands.Cog.listener()
    async def on_message_edit(self, ctx_bef: discord.Message, ctx_aft: discord.Message) -> None:
        # Get log channel
        async with self.bot.pool.acquire() as con:
            channel = await con.execute("SELECT log_channel FROM serverdata WHERE guild_id=$1", ctx_bef.guild.id)

        # Test if channel is null and return
        if channel is None:
            return

        # Get log level
        async with self.bot.pool.acquire() as con:
            level = await con.execute("SELECT log_level FROM serverdata WHERE guild_id=$1", ctx_bef.guild.id)

        # Check log level
        if level < 1:
            return

        # Edited message embed
        embed = discord.Embed(colour=discord.Colour.gold())
        embed.set_author(name=ctx_bef.author.display_name, icon_url=ctx_bef.author.display_avatar)
        embed.add_field(name='Message Alert: Edit', value=f'A message sent by {ctx_bef.author.mention} was edited in {ctx_bef.channel.mention}\n[View Message]({ctx_aft.jump_url})', inline=False)
        # Ignore impossible message
        try:
            embed.add_field(name='Before', value=ctx_bef.content, inline=False)
        except discord.errors.HTTPException:
            return
        except HTTPException:
            return
        else:
            embed.add_field(name='After', value=ctx_aft.content, inline=False)
            embed.set_footer(text=f'{datetime.now().strftime("%d/%m/%y - %H:%M:%S")}')

        # Send to channel
        await self.bot.get_channel(channel).send(embed=embed)

    # Log message deletions (level 1)
    @commands.Cog.listener()
    async def on_message_delete(self, ctx: discord.Message) -> None:
        # Get log channel
        async with self.bot.pool.acquire() as con:
            channel = await con.execute("SELECT log_channel FROM serverdata WHERE guild_id=$1", ctx.guild.id)

        # Test if channel is null and return
        if channel is None:
            return

        # Get log level
        async with self.bot.pool.acquire() as con:
            level = await con.execute("SELECT log_level FROM serverdata WHERE guild_id=$1", ctx.guild.id)

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
        except discord.errors.HTTPException:
            return
        except HTTPException:
            return
        embed.set_footer(text=f'{datetime.now().strftime("%d/%m/%y - %H:%M:%S")}')

        # Send to channel
        await self.bot.get_channel(channel).send(embed=embed)

    # Set log channel
    @app_commands.command(
        name='setchannel',
        description="Sets the channel server logs will be sent to"
    )
    @commands.has_role('bot manager')
    async def logging_setchannel(self, interaction: discord.Interaction, channel: str) -> None:
        # Update log channel
        async with self.bot.pool.acquire() as con:
            await con.execute("UPDATE serverdata SET log_channel=$2 WHERE guild_id=$1", interaction.guild.id, get_id(channel))

        # Respond
        await interaction.response.send_message("Log channel saved", ephemeral=False)

    # Set log level
    @app_commands.command(
        name='setlevel',
        description="Sets the level server logs will track"
    )
    @commands.has_role('bot manager')
    async def logging_setlevel(self, interaction: discord.Interaction,
                               level: Literal['0: None', '1: Default', '2: All Messages', '3: All Voice Activity', '4: All Activity']) -> None:
        # Update log level
        async with self.bot.pool.acquire() as con:
            await con.execute("UPDATE serverdata SET log_level=$2 WHERE guild_id=$1", interaction.guild.id, level)

        # Respond
        await interaction.response.send_message('Log level saved', ephemeral=False)


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(logging(bot))