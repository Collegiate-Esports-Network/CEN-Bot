__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '2.0.0'
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


class reactionroles(commands.Cog):
    """These are all functions available for role reaction managment.
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot
        self.reactfile = Path('cogs/json files/reactionroles.json')

        # Create file if it doesn't exist
        if not self.reactfile.is_file():
            self.reactfile.touch()

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
        # Init
        payload = JsonInteracts.Guilds.read_json(self.reactfile, ctx.guild.id)

        # Check if command user is giving input
        def checkuser(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        # Set new channel
        await ctx.send('What is the channel for role reactions?')
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
        except asyncio.TimeoutError:
            await ctx.send('Command has timed out')
            return
        else:
            payload['Channel'] = msg.content

        # Write to file
        JsonInteracts.Guilds.write_json(self.reactfile, payload, ctx.guild.id)

        # Send confirmation
        await ctx.send('React channel set.')

    # Add reactions to server
    @commands.command(
        name='reactadd',
        aliases=['addreact'],
        brief='Adds roles to role reactions',
        help='Adds role reactions to the masterlist of all role reactions and updates the reaction embeds'
    )
    @commands.has_role('Bot Manager')
    async def reactadd(self, ctx):
        # Init
        payload = JsonInteracts.Guilds.read_json(self.reactfile, ctx.guild.id)

        # Check if command user is giving input
        def checkuser(user):
            return user.author == ctx.author and user.channel == ctx.channel

        # Check if react channel is set, if not, set it
        try:
            self.bot.get_channel(get_id(payload['Channel']))
        except KeyError:
            # Prompt
            await ctx.send('React channel is not set! What is the channel for role reactions?')

            # Await response
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
            except asyncio.TimeoutError:
                ctx.send('Command has timed out.')
                return
            else:
                payload['Channel'] = msg.content

        # Check if role reactions already exist
        try:
            reactions = payload['Reactions']
        except KeyError:
            # Create empty dict
            payload['Reactions'] = {}

            # Reassign
            reactions = payload['Reactions']

        # Get category of reactions
        await ctx.send('What is the reaction category?')

        # Await response
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
        except asyncio.TimeoutError:
            ctx.send('Command has timed out.')
            return
        else:
            category = msg.content

        # Check for new category
        try:
            reactions[category]
        except KeyError:
            # Create empty dicti
            reactions[category] = {}

            # Prompt for category descriptionn
            await ctx.send('New category created. What is the category description?')
            try:
                msg = await self.bot.wait_for('message', timeout=60.0, check=checkuser)
            except asyncio.TimeoutError:
                await ctx.send('Command has timed out')
                return
            else:
                # Create category frame
                reactions[category]['Description'] = msg.content
                reactions[category]['Roles'] = {}

        # Get new role
        await ctx.send('Please mention the role you are adding.')

        # Await response
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
        except asyncio.TimeoutError:
            ctx.send('Command has timed out.')
            return
        else:
            role = msg.content

        # Check for new role
        try:
            reactions[category]['Roles'][role]
        except KeyError:
            # Create empty dict
            reactions[category]['Roles'][role] = {}

            # Prompt for role description
            await ctx.send('New reaction created. What is the role description?')
            try:
                msg = await self.bot.wait_for('message', timeout=60.0, check=checkuser)
            except asyncio.TimeoutError:
                await ctx.send('Command has timed out')
                return
            else:
                reactions[category]['Roles'][role]['Description'] = msg.content

            # Prompt for react emoji
            await ctx.send('What is the emoji for this reaction?')
            try:
                msg = await self.bot.wait_for('message', timeout=60.0, check=checkuser)
            except asyncio.TimeoutError:
                await ctx.send('Command has timed out')
                return
            else:
                reactions[category]['Roles'][role]['Emoji'] = msg.content
        else:
            await ctx.send('Reaction role already exists!')
            return

        # Update payload
        payload['Reactions'] = reactions

        # Dump into json
        JsonInteracts.Guilds.write_json(self.reactfile, payload, ctx.guild.id)

        # Send confirmation
        await ctx.send('Reaction added.')

    # Remove reaction role from server
    @commands.command(
        name='reactremove',
        aliases=['removereaction'],
        brief='Removes a role reaction',
        help='Removes a reaction role from the server'
    )
    @commands.has_role('Bot Manager')
    async def reactremove(self, ctx):
        # Init
        payload = JsonInteracts.Guilds.read_json(self.reactfile, ctx.guild.id)

        # Check if react channel exists
        try:
            self.bot.get_channel(get_id(payload['Channel']))
        except KeyError:
            await ctx.send('React channel not set! Please use "$setreactchannel" to set one.')
            return

        # Check if command user is giving input
        def checkuser(user):
            return user.author == ctx.author and user.channel == ctx.channel

        # Get react category
        await ctx.send('What is the category of the reaction?')
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
        except asyncio.TimeoutError:
            await ctx.send('Command has timed out')
            return
        else:
            category = msg.content

        # Get reaction id
        await ctx.send('Please mention the role you wish to remove.')
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
        except asyncio.TimeoutError:
            await ctx.send('Command has timed out')
            return
        else:
            role = msg.content

        # Search through database and remove
        reactions = payload['Reactions']
        reactions[category]['Roles'].pop(role)
        # removedreaction = reactions[category]['Roles'].pop(role)

        # Remove reaction from reaction roles embed
        # await msg.clear_reaction(removedreaction['Emoji'])  #FIXME: Does not remove reactions

        # Update payload
        payload['Reactions'] = reactions

        # Save changes
        JsonInteracts.Guilds.write_json(self.reactfile, payload, ctx.guild.id)

        # Send confirmation
        await ctx.send('Reaction removed.')

    # Creates/updates embed for reaction channel
    @commands.command(
        name='reactupdate',
        brief='Updates embed for reaction channel',
        help='Updates embed for reaction channel'
    )
    @commands.has_role('Bot Manager')
    async def reactupdate(self, ctx):
        # Init
        payload = JsonInteracts.Guilds.read_json(self.reactfile, ctx.guild.id)

        # Check if react channel exists
        try:
            react_channel = self.bot.get_channel(get_id(payload['Channel']))
        except KeyError:
            await ctx.send('React channel not set! Please use "$setreactchannel" to set one.')
            return

        # Check if reaction roles exist
        try:
            react_roles = payload['Reactions']
        except KeyError:
            await ctx.send('No reactions added! Please use "$reactadd" to add one.')
            return

        # Create embeds
        for category in react_roles:
            # Create text
            embed = discord.Embed(title=f'{category} Roles', description=react_roles[category]['Description'])
            for role in react_roles[category]['Roles']:
                roleID = get_id(role)
                roleName = discord.utils.get(ctx.guild.roles, id=roleID)
                desc = react_roles[category]['Roles'][role]['Description']
                emoji = react_roles[category]['Roles'][role]['Emoji']

                # Check if description is blank (N/A)
                if desc != 'N/A':
                    embed.add_field(name=f'{emoji} {roleName}', value=desc, inline=True)
                else:
                    embed.add_field(name=f'{emoji} {roleName}', inline=True)

            # Check if embed exists and edit, else create
            try:
                msg = await react_channel.fetch_message(get_id(react_roles[category]['Embed']))
            except KeyError:
                msg = await react_channel.send(embed=embed)
                # Mark as category embed
                react_roles[category]['Embed'] = msg.id
            else:
                await msg.edit(embed=embed)

            # Clear reactions
            await msg.clear_reactions()  # FIXME: Remove once $reactremove removes reaction

            # Add reactions
            for role in react_roles[category]['Roles']:
                emoji = react_roles[category]['Roles'][role]['Emoji']
                await msg.add_reaction(emoji)
        # Update payload
        payload['Reactions'] = react_roles

        # Dump into .json
        JsonInteracts.Guilds.write_json(self.reactfile, payload, ctx.guild.id)

        # Send confirmation
        await ctx.send('Reaction embed updated.')

    # Add role on reaction
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Ignore if bot reacted
        if user == self.bot.user:
            return

        # If no channel is set-up for guild, return
        try:
            payload = JsonInteracts.Guilds.read_json(self.reactfile, reaction.message.guild.id)
        except KeyError:
            return

        # Parse data
        react_channel = self.bot.get_channel(get_id(payload['Channel']))
        reactions = payload['Reactions']

        # Get reactions and their roles
        emojiRole = {}
        emojiList = []
        for category in reactions:
            for role in reactions[category]['Roles']:
                emoji = reactions[category]['Roles'][role]['Emoji']
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

        # If no channel is set-up for guild, return
        try:
            payload = JsonInteracts.Guilds.read_json(self.reactfile, reaction.message.guild.id)
        except KeyError:
            return

        # Parse data
        react_channel = self.bot.get_channel(get_id(payload['Channel']))
        reactions = payload['Reactions']

        # Get reactions and their roles
        emojiRole = {}
        emojiList = []
        for category in reactions:
            for role in reactions[category]['Roles']:
                emoji = reactions[category]['Roles'][role]['Emoji']
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
    bot.add_cog(reactionroles(bot))