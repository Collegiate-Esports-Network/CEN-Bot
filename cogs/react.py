__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Reaction role functions"""

# Python imports
from pathlib import Path
from typing import Optional

# Discord imports
import discord
from discord import Interaction
from discord.ext import commands
from discord import app_commands

# Custom imports
from utils import JsonInteracts, get_id


class react(commands.GroupCog, name='react'):
    """These are the reaction role functions
    """
    # Init
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.react_file = Path('data/react.json')
        self.react_data = JsonInteracts.read(self.react_file)
        self.save_timer = 10
        super().__init__()

    # Set reaction channel
    @app_commands.command(
        name='setchannel',
        description='Sets the reaction channel'
    )
    @app_commands.describe(
        channel='The channel mention'
    )
    @commands.has_role('bot manager')
    async def react_setchannel(self, interaction: Interaction, channel: str) -> None:
        # Test is this guild exists in memory
        try:
            self.react_data[str(interaction.guild_id)]
        except KeyError:
            self.react_data[str(interaction.guild_id)] = {
                "Channel": get_id(channel),
                "Categories": {}
            }
        else:
            self.react_data[str(interaction.guild_id)]['Channel'] = get_id(channel)

        # Save
        JsonInteracts.write(self.react_file, self.react_data)

        # Respond
        await interaction.response.send_message('SUCCESS: Reaction channel saved', ephemeral=True)

    # Add a reaction role
    @app_commands.command(
        name='add',
        description='Add a reaction role'
    )
    @app_commands.describe(
        category='The category of the reaction',
        cdesc='The category description',
        role='The role to add',
        rdesc='The role description',
        emoji='The reaction emoji'
    )
    @commands.has_role('bot manager')
    async def react_add(self, interaction: Interaction, category: str, role: str, emoji: str, cdesc: Optional[str] = None, rdesc: Optional[str] = None) -> None:
        # Test is this guild exists in memory
        try:
            self.react_data[str(interaction.guild_id)]
        except KeyError:
            self.react_data[str(interaction.guild_id)] = {
                "Channel": None,
                "Categories": {}
            }
        else:
            # Assign sub-group
            categories = self.react_data[str(interaction.guild_id)]['Categories']

        # Test if category exists
        try:
            categories[category]
        except KeyError:
            categories[category] = {
                "Description": cdesc,
                "Embed": None,
                "Roles": {}
            }

        # Parse roles
        roles = categories[category]['Roles']

        # Test if role exists
        try:
            roles[str(get_id(role))]
        except KeyError:
            roles[str(get_id(role))] = {
                "Description": rdesc,
                "Emoji": emoji
            }
            await interaction.response.send_message('SUCCESS: Role added!', ephemeral=True)
        else:
            await interaction.response.send_message('ERROR: That role already exists!', ephemeral=True)
            return

        # Merge changes
        categories[category]['Roles'] = roles
        self.react_data[str(interaction.guild_id)]['Categories'] = categories

        # Save
        JsonInteracts.write(self.react_file, self.react_data)

    # Remove a reaction role
    @app_commands.command(
        name='remove',
        description='Remove a reaction role'
    )
    @app_commands.describe(
        category='The category of the reaction',
        role='The role to remove',
    )
    @commands.has_role('bot manager')
    async def react_remove(self, interaction: Interaction, category: str, role: str) -> None:
        # Test is this guild exists in memory
        try:
            self.react_data[str(interaction.guild_id)]
        except KeyError:
            await interaction.response.send_message('ERROR: No reactions exist!', ephemeral=True)
        else:
            # Assign sub-group
            categories = self.react_data[str(interaction.guild_id)]['Categories']

        # Test if category exists
        try:
            categories[category]
        except KeyError:
            await interaction.response.send_message('ERROR: That category does not exist!', ephemeral=True)

        # Parse roles
        roles = categories[category]['Roles']

        # Test if role exists
        try:
            roles[str(get_id(role))]
        except KeyError:
            await interaction.response.send_message('ERROR: That role does not exist!', ephemeral=True)
        else:
            roles.pop(str(get_id(role)))
            await interaction.response.send_message('SUCCESS: That role was removed!', ephemeral=True)
            return

        # Merge changes
        categories[category]['Roles'] = roles
        self.react_data[str(interaction.guild_id)]['Categories'] = categories

        # Save
        JsonInteracts.write(self.react_file, self.react_data)

    # Send the embeds to the react channel
    @app_commands.command(
        name='send',
        description='Sends the reaction role embeds to the channel'
    )
    @commands.has_role('bot manager')
    async def react_send(self, interaction: Interaction) -> None:
        # Check if reaction channel exists
        try:
            self.react_data[str(interaction.guild_id)]['Channel']
        except KeyError:
            await interaction.response.send_message('ERROR: Reaction channel not set!', ephemeral=True)
            return
        else:
            channel = self.react_data[str(interaction.guild_id)]['Channel']
            if channel is None:
                await interaction.response.send_message('ERROR: Reaction channel not set!', ephemeral=True)
                return
            else:
                # Get channel object
                channel = self.bot.get_channel(channel)

        # Check if reactions exist
        try:
            self.react_data[str(interaction.guild_id)]['Categories']
        except KeyError:
            await interaction.response.send_message('ERROR: Reactions do not exist!', ephemeral=True)
            return
        else:
            categories = self.react_data[str(interaction.guild_id)]['Categories']

        # Create embeds and send
        for category in categories:
            category = categories[category]
            # Create embed
            desc = category['Description']
            if desc is None:
                embed = discord.Embed(title=f'{category} Roles')
            else:
                embed = discord.Embed(title=f'{category} Roles', description=desc)

            # Populate embed
            for role in category['Roles']:
                # Init
                roleName = discord.utils.get(interaction.guild.roles, id=get_id(role)).name
                desc = category['Roles'][role]['Description']
                emoji = category['Roles'][role]['Emoji']

                # Check if description is blank (N/A)
                if desc is None:
                    embed.add_field(name=f'{emoji} {roleName}', inline=True)
                else:
                    embed.add_field(name=f'{emoji} {roleName}', value=desc, inline=True)

            # Check if embed exists and edit, else create
            if category['Embed'] is None:
                msg = await channel.send(embed=embed)
                # Mark as category embed
                category['Embed'] = msg.id

                # Merge
                self.react_data[str(interaction.guild_id)]['Categories'] = category

                # Save
                JsonInteracts.write(self.react_file, self.react_data)
            else:
                msg = await channel.fetch_message(get_id(category['Embed']))
                await msg.edit(embed=embed)

            # Clear previous reactions
            await msg.clear_reactions()  # FIXME: Remove once $reactremove removes reaction

            # Add reactions
            for role in category['Roles']:
                emoji = role['Emoji']
                await msg.add_reaction(emoji)

    # Add or remove role on reaction
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, member: discord.Member) -> None:
        # Ignore if bot reacted
        if member == self.bot.user:
            return

        # Remove reaction
        await reaction.remove(member)

        # If no channel is set-up for guild, return
        try:
            self.react_data[str(reaction.message.guild.id)]['Channel']
        except KeyError:
            return
        else:
            channel = self.react_data[str(reaction.message.guild.id)]['Channel']
            channel = self.bot.get_channel(channel)

        # Get a list of all emojis
        emojiRole = {}
        emojiList = []
        categories = self.react_data[str(reaction.message.guild_id)]['Categories']
        for category in categories:
            for role in category['Roles']:
                # Get reactions and their roles
                emoji = role['Emoji']
                emojiList.append(emoji)
                emojiRole[emoji] = get_id(role)

        # Check if reaction occured in reaction channel, else ignore
        if reaction.message.channel == channel:
            # Check if valid reaction
            if reaction.emoji in emojiList:
                roleID = emojiRole[reaction.emoji]
                role = discord.utils.get(member.guild.roles, id=roleID)

                # Check if person already has role, add or remove on case
                if role in member.roles:
                    await member.remove_roles(role)
                else:
                    await member.add_roles(role)
            else:
                return
        else:
            return


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(react(bot))