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
from utils import JsonInteracts, get_id


class rolereactions(commands.Cog):
    """These are all functions available for role reaction managment.
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot
        self.reactfile = Path('cogs/json files/reactionroles.json')

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
    @commands.has_role('Bot Manager')
    async def setreactchannel(self, ctx):
        # Check if file exists, else create
        if self.reactfile.is_file():
            payload = JsonInteracts.Guilds.read_json(self.reactfile, ctx.guild.id)
        else:
            self.reactfile.touch()
            payload = {}

        # Check if command user is giving input
        def checkuser(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        # Set new channel
        await ctx.send('What is the channel for role reactions?')
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
        except asyncio.TimeoutError:
            await ctx.send('Command has timed out')
        else:
            payload['Channel'] = msg.content

        # Write to file
        JsonInteracts.Guilds.write_json(self.reactfile, payload, ctx.guild.id)

    # Creates/updates embed for reaction channel
    @commands.command(
        name='reactupdate',
        brief='Updates embed for reaction channel',
        help='Updates embed for reaction channel'
    )
    @commands.has_role('Bot Manager')
    async def reactupdate(self, ctx):
        # Try to open reactions file, send error if not
        try:
            payload = JsonInteracts.Guilds.read_json(self.reactfile, ctx.guild.id)
        except FileNotFoundError:
            await ctx.send('ERROR: Reaction channel not set')
        except KeyError:
            await ctx.send('ERROR: Reaction channel not set')

        # Parse data
        react_channel = self.bot.get_channel(get_id(payload['Channel']))
        react_roles = payload['Roles']

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

    # Add reactions to server
    @commands.command(
        name='reactadd',
        aliases=['addreact'],
        brief='Adds roles to role reactions',
        help='Adds role reactions to the masterlist of all role reactions and updates the reaction embeds'
    )
    @commands.has_role('Bot Manager')
    async def reactadd(self, ctx):
        # Test if reaction channel is set-up
        try:
            JsonInteracts.Guilds.read_json(self.reactfile, ctx.guild.id)
        except KeyError:
            await ctx.send('Reaction channel not set.')
            self.bot.get_command('setreactchannel')
        
        # Get reaction payload
        payload = JsonInteracts.Guilds.read_json(self.reactfile, ctx.guild.id)
        
        # Test if reaction roles have been created already
        try:
            payload['Roles']
        except KeyError:
            payload['Roles'] = {}
        
        # Parse payload
        react_channel = self.bot.get_channel(get_id(payload['Channel']))
        react_roles = payload['Roles']

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
            react_roles[newrole[Qs[0]]]
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
                react_roles[newrole[Qs[0]]] = {'Description': cDescription, 'Roles': {}}
        finally:
            # Check for new role
            try:
                react_roles[newrole[Qs[0]]]['Roles'][newrole[Qs[1]]]
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
                        react_roles[newrole[Qs[0]]]['Roles'][newrole[Qs[1]]] = {'Description': rDescription, "Emoji": emoji}
            else:
                await ctx.send('That role reaction already exists!')
                return

        # Combine payload
        payload['Channel'] = react_channel
        payload['Roles'] = react_roles

        # Dump into .json
        JsonInteracts.Guilds.write_json(self.reactfile, payload, ctx.guild.id)

        # Update embed
        # await self.bot.get_command('reactupdate')(ctx)    FIXME: Needs to edit embeds

    # Add role on reaction
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Ignore if bot reacted
        if user == self.bot.user:
            return

        # Try to open reactions file, send error if not
        try:
            payload = JsonInteracts.Guilds.read_json(self. eactionsfile, reaction.guild.id)
        except FileNotFoundError:
            return
        except KeyError:
            return

        # Parse data
        react_channel = self.bot.get_channel(get_id(payload['Channel']))
        react_roles = payload['Roles']

        # Get reactions and their roles
        emojiRole = {}
        emojiList = []
        for category in react_roles:
            for role in react_roles[category]['Roles']:
                emoji = react_roles[category]['Roles'][role]['Emoji']
                emojiList.append(emoji)
                emojiRole[emoji] = get_id(role)

        # Check if reaction occuredc in reaction channel, else ignore
        if reaction.message.channel == react_channel:
            # Check if valid reaction and add role, else return
            if reaction.emoji in emojiList:
                roleID = emojiRole[reaction.emoji]
                role = discord.utils.get(user.guild.roles, id=roleID)
                await user.add_roles(role)
                logging.info(f'{role} has been given to {user.display_name} in {user.guild}')
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

        # Try to open reactions file, send error if not
        try:
            payload = JsonInteracts.Guilds.read_json(self.reactionsfile, reaction.guild.id)
        except FileNotFoundError:
            return
        except KeyError:
            return

        # Parse data
        react_channel = self.bot.get_channel(get_id(payload['Channel']))
        react_roles = payload['Roles']

        # Get reactions and their roles
        emojiRole = {}
        emojiList = []
        for category in react_roles:
            for role in react_roles[category]['Roles']:
                emoji = react_roles[category]['Roles'][role]['Emoji']
                emojiList.append(emoji)
                emojiRole[emoji] = get_id(role)

        # Check if reaction occuredc in reaction channel, else ignore
        if reaction.message.channel == react_channel:
            # Check if valid reaction and add role, else return
            if reaction.emoji in emojiList:
                roleID = emojiRole[reaction.emoji]
                role = discord.utils.get(user.guild.roles, id=roleID)
                await user.remove_roles(role)
                logging.info(f'{role} has been removed from {user.display_name} in {user.guild}')
            else:
                return
        else:
            return


# Add to bot
def setup(bot) -> None:
    bot.add_cog(rolereactions(bot))