__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = 'Production'
__doc__ = """Logs messages and edits in discord servers"""

# Python imports
from pathlib import Path
import logging
from datetime import datetime

# Discord imports
import discord
from discord.ext import commands

# Custom imports
from utils import JsonInteracts
from utils import get_id

# Redef
read_json = JsonInteracts.read_json
write_json = JsonInteracts.write_json


class activitylog(commands.Cog):
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot

    # Check if loaded
    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('Logging Cog loaded')

    # Choose log channel
    @commands.command(
        name='setlogchannel',
        brief='Chooses a channel to log information to',
        help='Chooses a channel to log information to'
    )
    async def setlogchannel(self, ctx):
        # Init
        path = Path('cogs/json files/loggingchannel.json')

        # Check if file exits, else create
        if path.is_file():
            channel = read_json(path)
        else:
            path.touch()
            channel = dict()

        # Check if command user is giving input
        def checkuser(user):
            return user.author == ctx.author and user.channel == ctx.channel

        # Set new channel
        await ctx.send('What is the channel for message logging?')
        msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
        channel['Channel'] = msg.content

        # Write to file
        write_json(path, channel)

    # Log message edits
    @commands.Cog.listener()
    async def on_message_edit(self, ctx_bef, ctx_aft):
        # Get logging channel
        try:
            channel = read_json(Path('cogs/json files/loggingchannel.json'))['Channel']
        except FileNotFoundError:
            return
        else:
            channel = get_id(channel)
            channel = self.bot.get_channel(channel)

        # Edited message embed
        embed = discord.Embed(colour=discord.Colour.gold())
        embed.set_author(name=ctx_bef.author.display_name, icon_url=ctx_bef.author.avatar_url)
        embed.add_field(name='Message Alert: Edit', value=f'A message sent by {ctx_bef.author.mention} was edited in {ctx_bef.channel.mention}\n[View Message]({ctx_aft.jump_url})', inline=False)
        embed.add_field(name='Before', value=ctx_bef.content, inline=False)
        embed.add_field(name='After', value=ctx_aft.content, inline=False)
        embed.set_footer(text=f'{datetime.now().strftime("%d/%m/%y - %H:%M:%S")}')

        # Send to channel
        await channel.send(embed=embed)

    # Log message deletion
    @commands.Cog.listener()
    async def on_message_delete(self, ctx):
        # Get logging channel
        try:
            channel = read_json(Path('cogs/json files/loggingchannel.json'))['Channel']
        except FileNotFoundError:
            return
        else:
            channel = get_id(channel)
            channel = self.bot.get_channel(channel)

        # Deleted message embed
        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.add_field(name='Message Alert: Deletion', value=f'A message sent by {ctx.author.mention} was deleted in {ctx.channel.mention}', inline=False)
        embed.add_field(name='Content', value=ctx.content)
        embed.set_footer(text=f'{datetime.now().strftime("%d/%m/%y - %H:%M:%S")}')

        # Send to channel
        await channel.send(embed=embed)


# Add to bot
def setup(bot) -> None:
    bot.add_cog(activitylog(bot))