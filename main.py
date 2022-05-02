__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '0.1.0'
__status__ = 'Indev'
__doc__ = """Main file of the CEN Discord Bot"""

# Python imports
import os
from dotenv import load_dotenv
import logging

# Discord imports
import discord
from discord.ext.commands import Bot

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TOKEN')[1:-1]

# Init logging
logging.basicConfig(filename='LOGGING.log', encoding='UTF-8', level=logging.INFO)

# Init bot
intents = discord.Intents.all()
activity = discord.Activity(type=discord.ActivityType.watching, name='for $<command>')
bot = Bot(intents=intents, activity=activity, command_prefix='$')


# Verify login
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to the Discord!')


# Embed current bot info
@bot.command(name='info')
async def fetchbotinfo(ctx):
    """
    Returns relevent bot information
    """
    embed = discord.Embed(title='Bot Info', description='Here is the most up-to-date information on the bot', color=0x2374a5)
    icon = discord.File('L1.png', filename='L1.png')
    embed.set_author(name='CEN Bot', icon_url='attachment://L1.png')
    embed.add_field(name="Bot Version", value=__version__)
    embed.add_field(name='Written By', value='Justin Panchula and Zach Lesniewski')
    embed.add_field(name='Server Information', value=f'This bot is in {len(bot.guilds)} servers watching over {len(set(bot.get_all_members()))} members.', inline=False)
    embed.set_footer(text=f'Information requested by: {ctx.author.display_name}')

    await ctx.send(file=icon, embed=embed)


# Run
bot.run(TOKEN)