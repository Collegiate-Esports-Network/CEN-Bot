__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '0.1.0'
__status__ = 'Indev'
__doc__ = """Role management functions"""

# Python imports
from pathlib import Path
import asyncio

# Discord imports
import logging
from discord.ext import commands

# Custom imports
from json_interacts import read_json, write_json


class rolemgmt(commands.Cog):
    """
    Role management functions
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot

    # Check if loaded
    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('Role Management Cog loaded')

    # Add reactions to file
    @commands.command(name='addreact')
    async def addreact(self, ctx):
        # Init
        path = Path.cwd()

        # Check if file exits, create if not
        if not Path('cogs/roles.json').is_file():
            path = Path('cogs/roles.json')
            path.touch()
        else:
            path = path.joinpath('cogs/roles.json')

        # Read in data already present
        roles = read_json(path)

        # Check if command user is giving input
        def check(user):
            return user.author == ctx.author and user.channel == ctx.channel

        # Prompts for user entry
        Qs = ['Role Category', 'Role Name', 'Role Emoji']
        newrole = {}

        # Ask questions and get answers
        for Q in Qs:
            await ctx.send(Q + '?')

            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send('Command has timed out')
                return
            else:
                newrole[Q] = msg.content

        # Append
        roles[newrole[Qs[1]]] = {Qs[0]: newrole[Qs[0]], Qs[2]: newrole[Qs[2]]}

        # Dump into roles.json
        write_json(path, roles)


# Add to bot
def setup(bot) -> None:
    bot.add_cog(rolemgmt(bot))
