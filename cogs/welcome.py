__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = 'Production'
__doc__ = """Welcome message functions"""

# Python imports
from pathlib import Path
import logging
import asyncio

# Discord imports
from discord.ext import commands

# Custom imports
from utils import JsonInteracts, get_id


class welcome(commands.Cog):
    """These are the welcome message functions
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot
        self.welcomefile = Path('cogs/json files/welcome.json')

        # Create file if it doesn't exist
        if not self.welcomefile.is_file():
            self.welcomefile.touch()

    # Check if loaded
    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('Welcome Cog loaded')

    # Set welcome channel
    @commands.command(
        name='setwelcomechannel',
        brief='Sets the welcome channel',
        help='Sets the welcome channel'
    )
    @commands.has_role('Bot Manager')
    async def setwelcomechannel(self, ctx):
        # Init
        payload = JsonInteracts.Guilds.read_json(self.welcomefile, ctx.guild.id)

        # Check if command user is giving input
        def checkuser(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        # Set new channel
        await ctx.send('What is the channel for the welcome message?')
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
        except asyncio.TimeoutError:
            await ctx.send('Command has timed out')
            return
        else:
            payload['Channel'] = msg.content

        # Write to file
        JsonInteracts.Guilds.write_json(self.welcomefile, payload, ctx.guild.id)

        # Send confirmation
        await ctx.send('Welcome channel set.')

    @commands.command(
        name='setwelcomemessage',
        brief='Sets the welcome message',
        help='Sets the welcome message'
    )
    @commands.has_role('Bot Manager')
    async def setwelcomemessage(self, ctx):
        # Init
        payload = JsonInteracts.Guilds.read_json(self.welcomefile, ctx.guild.id)

        # Check if command user is giving input
        def checkuser(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        # Check if channel is set, if not then set
        try:
            payload['Channel']
        except KeyError:
            # Set welcome channel
            await ctx.send('What is the channel for the welcome message?')
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=checkuser)
            except asyncio.TimeoutError:
                await ctx.send('Command has timed out')
                return
            else:
                payload['Channel'] = msg.content

        # Get welcome message
        await ctx.send('What is the welcome message? Use <new_user> where you want to message the incoming user.')
        try:
            msg = await self.bot.wait_for('message', timeout=180.0, check=checkuser)
        except asyncio.TimeoutError:
            await ctx.send('Command has timed out')
            return
        else:
            payload['Message'] = msg.content

        # Save
        JsonInteracts.Guilds.write_json(self.welcomefile, payload, ctx.guild.id)

        # Send confirmation
        await ctx.send('Welcome message saved')

    # Send new message on welcome
    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Init
        payload = JsonInteracts.Guilds.read_json(self.welcomefile, member.guild.id)

        # Get welcome channel
        try:
            welcome_channel = self.bot.get_channel(get_id(payload['Channel']))
        except KeyError:
            return

        # Get welcome message
        try:
            welcome_message = payload['Message']
        except KeyError:
            return

        # Edit welcome message to mention user
        welcome_message = welcome_message.replace('<new_user>', member.mention)

        # Send welcome message
        await welcome_channel.send(welcome_message)

        # Log member join
        logging.info(f'{member.name} joined {member.guild.name}')

    # Test welcome message
    @commands.command(
        name='testwelcomemessage',
        brief='Tests the welcome message',
        help='Tests the welcome message'
    )
    @commands.has_role('Bot Manager')
    async def testwelcomemessage(self, ctx):
        # Init
        payload = JsonInteracts.Guilds.read_json(self.welcomefile, ctx.guild.id)

        # Edit message to mention tests
        welcome_message = payload['Message']
        welcome_message = welcome_message.replace('<new_user>', ctx.author.mention)

        # Send message, mentioning user
        await ctx.send(welcome_message)


# Add to bot
def setup(bot) -> None:
    bot.add_cog(welcome(bot))