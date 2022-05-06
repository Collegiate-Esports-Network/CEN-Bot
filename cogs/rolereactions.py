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
import logging

# Discord imports
from discord.ext import commands

# Custom imports
from json_interacts import read_json, write_json


class rolereact(commands.Cog):
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot

    # Check if loaded
    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('Role Reaction Cog loaded')

    # Set role reaction channel
    @commands.command(
        name='setreactchannel',
        aliases=['setreactionchannel'],
        brief='Sets the reaction channel',
        help='Sets the reaction channel'
    )
    async def setreactchannel(self, ctx):
        # Init
        path = Path.cwd()

        # Check if file exits and create, else add to path and read
        if not Path('cogs/rolereactionchannel.json').is_file():
            path = Path('cogs/rolereactionchannel.json')
            path.touch()
            channel = dict()
        else:
            path = path.joinpath('cogs/rolereactionchannel.json')
            channel = read_json(path)

        # Check if command user is giving input
        def checkuser(user):
            return user.author == ctx.author and user.channel == ctx.channel

        # Set new channel
        await ctx.send('What is the channel for role reactions?')
        msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
        channel['Channel'] = msg.content

        # Write to file
        write_json(path, channel)

    # Creates/updates embed for channel
    @commands.command(
        name='updateroles',
        brief='Updates embed for reaction channel',
        help='Updates embed for reaction channel'
    )
    async def updateroles(self):
        return

    # Add reactions to file
    @commands.command(
        name='reactadd',
        brief='Adds roles to role reactions',
        help='Adds role reactions to the masterlist of all role reactions and updates the reaction embeds'
    )
    async def reactadd(self, ctx):
        # Init
        path = Path.cwd()

        # Check if file exits and create, else add to path and read
        if not Path('cogs/reactionroles.json').is_file():
            path = Path('cogs/reactionroles.json')
            path.touch()
            roles = dict()
        else:
            path = path.joinpath('cogs/reactionroles.json')
            roles = read_json(path)

        # Prompts for user entry
        Qs = ['Role Category', 'Role Name']
        newrole = dict()

        # Check if command user is giving input
        def checkuser(user):
            return user.author == ctx.author and user.channel == ctx.channel

        # Ask questions and get answers
        for Q in Qs:
            await ctx.send(Q + '?')

            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
            except asyncio.TimeoutError:
                await ctx.send('Command has timed out')
                return
            else:
                newrole[Q] = msg.content

        # Check for new category
        try:
            roles[newrole[Qs[0]]]
        except KeyError:
            # Ask for category description
            await ctx.send('New role category created. What is the category description?')
            try:
                msg = await self.bot.wait_for('message', timeout=60.0, check=checkuser)
            except asyncio.TimeoutError:
                await ctx.send('Command has timed out')
                return
            else:
                cDescription = msg.content
                roles[newrole[Qs[0]]] = {'Description': cDescription, 'Roles': {}}
        finally:
            # Check for new role
            try:
                roles[newrole[Qs[0]]]['Roles'][newrole[Qs[1]]]
            except KeyError:
                # Ask for role description and emoji
                await ctx.send('New role reaction created. What is the role description?')
                try:
                    msg1 = await self.bot.wait_for('message', timeout=60.0, check=checkuser)
                except asyncio.TimeoutError:
                    await ctx.send('Command has timed out')
                    return
                else:
                    await ctx.send('What is the role emoji?')
                    try:
                        msg2 = await self.bot.wait_for('message', timeout=60.0, check=checkuser)
                    except asyncio.TimeoutError:
                        await ctx.send('Command has timed out')
                        return
                    else:
                        # Populate
                        rDescription = msg1.content
                        emoji = msg2.content
                        roles[newrole[Qs[0]]]['Roles'][newrole[Qs[1]]] = {'Description': rDescription, "Emoji": emoji}
            else:
                await ctx.send('That role reaction already exists!')
                return

        # Dump into roles.json
        write_json(path, roles)

        await self.bot.get_command('updatereactionroles')


# Add to bot
def setup(bot) -> None:
    bot.add_cog(rolereact(bot))
