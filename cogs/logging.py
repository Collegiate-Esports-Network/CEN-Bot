__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Logs activity in discord servers"""

# Python imports
from pathlib import Path
from datetime import datetime
from http.client import HTTPException
from typing import Literal

# Discord imports
import discord
from discord.ext import commands
from discord import app_commands

# Custom imports
from utils import JsonInteracts, get_id


class logging(commands.GroupCog, name='logging'):
    """These are all the logging functions
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logging_file = Path('data/logging.json')
        self.logging_data = JsonInteracts.read(self.logging_file)
        self.save_timer = 10
        super().__init__()

    # Log message edits
    @commands.Cog.listener()
    async def on_message_edit(self, ctx_bef: discord.Message, ctx_aft: discord.Message) -> None:
        # Test if logging channel has been set
        try:
            channel = self.bot.get_channel(self.logging_data[str(ctx_bef.guild.id)]['Channel'])
        except KeyError:
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
        await channel.send(embed=embed)

        # Subtract 1 from timer
        self.save_timer -= 1

        # Check if save timer is up
        if self.save_timer <= 0:
            JsonInteracts.write(self.logging_file, self.logging_data)
            self.save_timer = 10

    # Log message deletions
    @commands.Cog.listener()
    async def on_message_delete(self, ctx: discord.Message) -> None:
        # Test if logging channel has been set
        try:
            channel = self.bot.get_channel(self.logging_data[str(ctx.guild.id)]['Channel'])
        except KeyError:
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
        await channel.send(embed=embed)

        # Subtract 1 from timer
        self.save_timer -= 1

        # Check if save timer is up
        if self.save_timer <= 0:
            JsonInteracts.write(self.logging_file, self.logging_data)
            self.save_timer = 10

    # Set log channel
    @app_commands.command(
        name='setchannel',
        description='Sets the channel server logs will be sent to'
    )
    @commands.has_role('bot manager')
    async def logging_setchannel(self, interaction: discord.Interaction, channel: str) -> None:
        # Test is this guild exists in memory
        try:
            self.logging_data[str(interaction.guild_id)]
        except KeyError:
            self.logging_data[str(interaction.guild_id)] = {}

        # Test if channel has been created
        try:
            self.logging_data[str(interaction.guild_id)]['Channel']
        except KeyError:
            self.logging_data[str(interaction.guild_id)]['Channel'] = ''

        # Set log channel
        self.logging_data[str(interaction.guild_id)]['Channel'] = get_id(channel)

        # Respond
        await interaction.response.send_message('Log channel saved', ephemeral=True)

    # Set log level
    @app_commands.command(
        name='setlevel',
        description='Sets the level server logs will track'
    )
    @commands.has_role('bot manager')
    async def logging_setlevel(self, interaction: discord.Interaction, level: Literal['0: None', '1: Default', '2: All Messages', '3: All Voice Activity', '4: All Activity']) -> None:
        # Test is this guild exists in memory
        try:
            self.logging_data[str(interaction.guild_id)]
        except KeyError:
            self.logging_data[str(interaction.guild_id)] = {}

        # Test if level has been created
        try:
            self.logging_data[str(interaction.guild_id)]['Level']
        except KeyError:
            self.logging_data[str(interaction.guild_id)]['Level'] = ''

        # Set log level
        self.logging_data[str(interaction.guild_id)]['Level'] = level

        # Respond
        await interaction.response.send_message('Log level saved', ephemeral=True)


# Add to bot
async def setup(bot) -> None:
    await bot.add_cog(logging(bot))