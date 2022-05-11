__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = 'Production'
__doc__ = """xp Functions"""

# Python imports
from time import time
from pathlib import Path
import logging
import random
from collections import Counter

# Discord imports
import discord
from discord.ext import commands

# Cutom imports
from utils import JsonInteracts, get_id


class xp(commands.Cog):
    """These are all functions dealing with xp
    """
    # Init
    def __init__(self, bot) -> None:
        self.bot = bot
        self.xpfile = Path('cogs/json files/xp.json')

    # Check if loaded
    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('xp Cog loaded')
    
    # Generates xp for users on message
    @commands.Cog.listener()
    async def on_message(self, ctx):
        # Ignore bot messages
        if self.bot.user == ctx.author:
            return

        # Check if file exists, else create
        if self.xpfile.is_file():
            xplog = JsonInteracts.Guilds.read_json(self.xpfile, ctx.guild.id)
        else:
            self.xpfile.touch()
            xplog = {}
        
        # Generate random number between 1 and 100
        random.seed(round(time() * 1000))
        num = random.randint(1, 100)

        # Try to give xp, else initialize and give them 1
        try:
            xplog[str(ctx.author.id)]
        except KeyError:
            xplog[str(ctx.author.id)] = 1
        else:
            if num < 50:
                xplog[str(ctx.author.id)] += 0
            elif num < 70:
                xplog[str(ctx.author.id)] += 1
            elif num < 90:
                xplog[str(ctx.author.id)] += 2
            else:
                xplog[str(ctx.author.id)] += 3
        
        # Write to file
        JsonInteracts.Guilds.write_json(self.xpfile, xplog, ctx.guild.id)
    
    # Get xp
    @commands.command(
        name='getxp',
        aliases=['xp'],
        brief='Returns your xp',
        help='Returns an individual\'s xp',
    )
    async def getxp(self, ctx):
        # Load xp log
        xplog = JsonInteracts.Guilds.read_json(self.xpfile, ctx.guild.id)

        # Tell users xp
        await ctx.send(f'Your xp in this server is: {xplog[str(ctx.author.id)]}')
    
    # Get leaderboard
    @commands.command(
        name='xpleaderboard',
        aliases=['leaderboard'],
        brief='Displays the xp leaderboard',
        help='Displays the server xp leaderboard'
    )
    async def leaderboard(self, ctx):
        # Load xp log
        xplog = JsonInteracts.Guilds.read_json(self.xpfile, ctx.guild.id)

        # Get top 20 xps
        k = Counter(xplog)
        top20 = k.most_common(20)

        # Create embed
        embed = discord.Embed(title='Top 20 xp Leaders')
        for key in top20:
            userID, xp = key
            username = self.bot.get_user(get_id(userID)).name
            embed.add_field(name=username, value=xp)
        
        # Send embed
        await ctx.send(embed=embed)


# Add to bot
def setup(bot) -> None:
    bot.add_cog(xp(bot))