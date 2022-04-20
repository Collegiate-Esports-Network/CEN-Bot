# Python imports
import os
from dotenv import load_dotenv

# Discord imports
import discord

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TOKEN')[1:-1]
# GUILD = os.getenv('GUILD')[1:-1]

# Init
client = discord.Client()


@client.event
async def on_ready():
    print(f'{client.user.name} has connected to the Discord!')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

# Run
client.run(TOKEN)