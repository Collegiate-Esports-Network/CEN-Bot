# Python libs
import os
from dotenv import load_dotenv
import logging

# Discord libs
import discord
from discord.ext.commands import Bot

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TOKEN')[1:-1]
# GUILD = os.getenv('GUILD')[1:-1]

# Init
intents = discord.Intents.all()
bot = Bot(intents=intents, command_prefix='$')

# Bot commands
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to the Discord!')


@bot.command(name='server')
async def fetchserverinfo(context):
    guild = context.guild

    await context.send(f'Server name: {guild.name}')
    await context.send(f'Server size: {len(guild.members)}')
    await context.send(f'Server owner: {guild.owner.display_name}')

# Run
bot.run(TOKEN)