__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula'
__license__ = 'MIT License'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """xp Functions"""

# Python imports
from pathlib import Path
import random
import time
from collections import Counter

# Discord imports
import discord
from discord.ext import commands
from discord import app_commands

# Custom imports
from cbot import cbot
from utils import JsonInteracts, get_id


class xp(commands.GroupCog, name='xp'):
    """ These are all functions related to the xp function of the bot.
    """
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        self.xp_file = Path('data/xp.json')
        self.xp_data = JsonInteracts.read(self.xp_file)
        self.save_timer = 10
        super().__init__()

    @commands.Cog.listener()
    async def on_message(self, ctx: discord.Message) -> None:
        # Ignore messages from test server
        if self.bot.user == ctx.author or ctx.guild.id == 0:  # 778306842265911296
            return
        
        # See if an xp log is already created for the server
        try:
            xp_guild = self.xp_data[str(ctx.guild.id)]
        except KeyError:
            xp_guild = {}

        # Generate random number between 1 and 100
        random.seed(round(time.time() * 1000))
        num = random.randint(1, 100)

        # Give xp to message sender
        try:
            xp_guild[str(ctx.author.id)]
        except KeyError:
            xp_guild[str(ctx.author.id)] = 1
        else:
            if num < 50:
                xp_guild[str(ctx.author.id)] += 0
            elif num < 70:
                xp_guild[str(ctx.author.id)] += 1
            elif num < 90:
                xp_guild[str(ctx.author.id)] += 2
            else:
                xp_guild[str(ctx.author.id)] += 3

        # Merge changes
        self.xp_data[str(ctx.guild.id)] = xp_guild

        # Subtract 1 from timer
        self.save_timer -= 1

        # Check if save timer is up
        if self.save_timer <= 0:
            JsonInteracts.write(self.xp_file, self.xp_data)
            self.save_timer = 10

    @app_commands.command(
        name='xp',
        description='Returns your current xp'
    )
    async def xp_xp(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f'Your xp in this server is: {self.xp_data[str(interaction.guild_id)][str(interaction.user.id)]}')

    @app_commands.command(
        name='leaderboard',
        description='Returns the top 20 xp leaders'
    )
    async def xp_leaderboard(self, interaction: discord.Interaction) -> None:
        # Get top 20 xps
        k = Counter(self.xp_data[str(interaction.guild_id)])
        top20 = k.most_common(20)

        # Create embed
        embed = discord.Embed(title='Top 20 xp Leaders')
        i = 1
        for key in top20:
            userID, xp = key
            username = self.bot.get_user(get_id(userID)).name
            embed.add_field(name=f'{i}. {username}', value=f'xp: {xp}', inline=False)
            i += 1

        await interaction.response.send_message(embed=embed, ephemeral=True)


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(xp(bot))