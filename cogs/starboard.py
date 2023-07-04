__author__ = "Chris Taylor"
__copyright__ = "Copyright CEN"
__credits__ = "Chris Taylor"
__version__ = "0.0.0"
__status__ = "Development"
__doc__ = """Starboard functions"""

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
from asyncpg.exceptions import PostgresError

logger = logging.getLogger("starboard")


class starboard(commands.GroupCog, name="starboard"):
    """These are the starboard functions."""

    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(starboard(bot))


# GPT4 stuff

# Create a Discord client
client = discord.Client()

 
@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    if meets_starboard_criteria(message):
        await add_to_starboard(message)


@client.event
async def on_reaction_add(reaction, user):
    if reaction.emoji == "⭐":  # Assuming the star emoji is ⭐
        message = reaction.message
        await update_star_count(message)


@client.event
async def on_reaction_remove(reaction, user):
    if reaction.emoji == "⭐":  # Assuming the star emoji is ⭐
        message = reaction.message
        await update_star_count(message)


async def add_to_starboard(message):
    starboard_channel_id = YOUR_STARBOARD_CHANNEL_ID

    # Get starboard channel
    starboard_channel = client.get_channel(starboard_channel_id)
    if not starboard_channel:
        return

    # Create a new entry on the starboard
    starboard_entry = f"Stars: {get_star_count(message)}\nAuthor: {message.author.mention}\nContent: {message.content}"
    await starboard_channel.send(starboard_entry)


async def remove_from_starboard(message):
    starboard_channel_id = YOUR_STARBOARD_CHANNEL_ID

    # Get starboard channel
    starboard_channel = client.get_channel(starboard_channel_id)
    if not starboard_channel:
        return

    # Iterate over starboard messages to find the corresponding entry and delete it
    async for starboard_message in starboard_channel.history():
        if starboard_message.content.endswith(
            f"Author: {message.author.mention}\nContent: {message.content}"
        ):
            await starboard_message.delete()
            break


async def update_star_count(message):
    starboard_channel_id = YOUR_STARBOARD_CHANNEL_ID

    # Get starboard channel
    starboard_channel = client.get_channel(starboard_channel_id)
    if not starboard_channel:
        return

    # Iterate over starboard messages to find the corresponding entry and update the star count
    async for starboard_message in starboard_channel.history():
        if starboard_message.content.endswith(
            f"Author: {message.author.mention}\nContent: {message.content}"
        ):
            star_count = get_star_count(message)
            new_entry = starboard_message.content.replace(
                f"Stars: {star_count - 1}", f"Stars: {star_count}"
            )
            await starboard_message.edit(content=new_entry)
            break


def meets_starboard_criteria(message):
    # Implement your criteria for qualifying a message for the starboard
    # For example, minimum star count, channel restrictions, etc.
    return get_star_count(message) >= YOUR_STAR_COUNT_THRESHOLD


def get_star_count(message):
    # Implement your logic to calculate the star count of a message
    # This can be based on the number of star reactions or any other criteria
    return len(
        [reaction for reaction in message.reactions if str(reaction.emoji) == "⭐"]
    )


# Run the Discord client
client.run("YOUR_BOT_TOKEN")
