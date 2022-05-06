__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = 'Production'
__doc__ = """Role management functions"""

# Python imports
from pathlib import Path
import asyncio
import logging

# Discord imports
import discord
from discord.ext import commands

# Custom imports
from utils import JsonInteracts
from utils import get_id

# Redef
read_json = JsonInteracts.read_json
write_json = JsonInteracts.write_json


class rolereactions(commands.Cog):
    """
    These are all functions available for role reaction managment.
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot

    # Check if loaded
    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('Role Reaction Cog loaded')

    # Set role reaction channel
    @commands.command(
        name='reactchannel',
        aliases=['setreactionchannel', 'setreactchannel'],
        brief='Sets the reaction channel',
        help='Sets the reaction channel'
    )
    @commands.has_role('Bot Manager')
    async def reactchannel(self, ctx):
        # Init
        path = Path('cogs/json files/rolereactionchannel.json')

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
        await ctx.send('What is the channel for role reactions?')
        msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
        channel['Channel'] = msg.content

        # Write to file
        write_json(path, channel)

    # Creates/updates embed for channel
    @commands.command(
        name='reactupdate',
        brief='Updates embed for reaction channel',
        help='Updates embed for reaction channel'
    )
    @commands.has_role('Bot Manager')
    async def reactupdate(self, ctx):
        # Try to open react channel file, pass error if not
        try:
            react_channel = read_json(Path('cogs/json files/rolereactionchannel.json'))['Channel']
        except FileNotFoundError:
            await ctx.send('Reaction channel not set')
            return
        except KeyError:
            await ctx.send('Reaction channel not set')
            return
        else:
            react_channel = get_id(react_channel)  # Formatting and typing channel id
            react_channel = self.bot.get_channel(react_channel)  # Getting channel object

        # Try to open reaction roles file, pass error if not
        try:
            react_roles = read_json(Path('cogs/json files/reactionroles.json'))
        except FileNotFoundError:
            await ctx.send('Reaction roles not created')
            return
        except KeyError:
            await ctx.send('Reaction roles not created')
            return

        # Create embeds per category
        for category in react_roles:
            embed = discord.Embed(title=f'{category} Roles', description=react_roles[category]['Description'])
            for role in react_roles[category]['Roles']:
                roleID = get_id(role)
                roleName = discord.utils.get(ctx.guild.roles, id=roleID)
                desc = react_roles[category]['Roles'][role]['Description']
                emoji = react_roles[category]['Roles'][role]['Emoji']
                embed.add_field(name=f'{emoji} {roleName}', value=desc, inline=True)
            msg = await react_channel.send(embed=embed)
            for role in react_roles[category]['Roles']:
                emoji = react_roles[category]['Roles'][role]['Emoji']
                await msg.add_reaction(emoji)

    # Add reactions to file
    @commands.command(
        name='reactadd',
        aliases=['addreact'],
        brief='Adds roles to role reactions',
        help='Adds role reactions to the masterlist of all role reactions and updates the reaction embeds'
    )
    @commands.has_role('Bot Manager')
    async def reactadd(self, ctx):
        # Init
        path = Path('cogs/json files/reactionroles.json')

        # Check if file exits, else create
        if path.is_file():
            roles = read_json(path)
        else:
            path.touch()
            roles = dict()

        # Prompts for user entry
        Qs = ['Role Category', 'Role Mention/ID']
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

        self.bot.get_command('reactupdate')(ctx)  # FIXME: Not calling "$reactupdate"

    # Add role on reaction
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Ignore if bot reacted
        if user == self.bot.user:
            return

        # Get reaction channel
        try:
            react_channel = read_json(Path('cogs/json files/rolereactionchannel.json'))['Channel']
        except FileNotFoundError:
            return
        else:
            react_channel = get_id(react_channel)
            react_channel = self.bot.get_channel(react_channel)

        # Get reaction roles
        react_roles = read_json(Path('cogs/json files/reactionroles.json'))

        # Get reactions and their roles
        emojirole = dict()
        emojiList = []
        for category in react_roles:
            for role in react_roles[category]['Roles']:
                emoji = react_roles[category]['Roles'][role]['Emoji']
                emojiList.append(emoji)
                emojirole[emoji] = get_id(role)

        # Check if reaction occured in reaction channel, else return
        if reaction.message.channel == react_channel:
            # Check if valid reaction and add role, else return
            if reaction.emoji in emojiList:
                roleID = emojirole[reaction.emoji]
                role = discord.utils.get(user.guild.roles, id=roleID)
                await user.add_roles(role)
                logging.info(f'{role} has been given {user.display_name} in {user.guild}')
            else:
                return
        else:
            return

    # Remove role on de-reaction
    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        # Ignore if bot reacted
        if user == self.bot.user:
            return

        # Get reaction channel
        try:
            react_channel = read_json(Path('cogs/json files/rolereactionchannel.json'))['Channel']
        except FileNotFoundError:
            return
        else:
            react_channel = get_id(react_channel)
            react_channel = self.bot.get_channel(react_channel)

        # Get reaction roles
        react_roles = read_json(Path('cogs/json files/reactionroles.json'))

        # Get reactions and their roles
        emojirole = dict()
        emojiList = []
        for category in react_roles:
            for role in react_roles[category]['Roles']:
                emoji = react_roles[category]['Roles'][role]['Emoji']
                emojiList.append(emoji)
                emojirole[emoji] = get_id(role)

        # Check if de-reaction occured in reaction channel, else return
        if reaction.message.channel == react_channel:
            # Check if valid de-reaction and remove, else return
            if reaction.emoji in emojiList:
                roleID = emojirole[reaction.emoji]
                role = discord.utils.get(user.guild.roles, id=roleID)
                await user.remove_roles(role)
                logging.info(f'{role} has been given to {user.display_name} in {user.guild}')
            else:
                return
        else:
            return


# Add to bot
def setup(bot) -> None:
    bot.add_cog(rolereactions(bot))
