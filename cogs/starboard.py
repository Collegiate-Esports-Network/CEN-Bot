__author__ = "Chris Taylor"
__copyright__ = "Copyright CEN"
__credits__ = "Chris Taylor, Justin Panchula"
__version__ = "1"
__status__ = "Production"
__doc__ = """Starboard functions"""

# Python imports
from datetime import datetime

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
from asyncpg.exceptions import PostgresError
log = logging.getLogger('CENBot.starboard')


@commands.guild_only()
class starboard(commands.GroupCog, name='starboard'):
    """These are the starboard functions.
    """
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()

    def create_embed(self, message: discord.Message, awarder: str) -> discord.Embed:
        embed = discord.Embed(color=discord.Color.from_str('#FF5733'), title="Starboard Message")
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar)
        embed.add_field(name='Message', value=f"{message.content}\n[View Message]({message.jump_url})", inline=False)
        embed.add_field(name="Awarded By", value=awarder, inline=False)
        embed.set_footer(text=f"Awarded at: {datetime.now().strftime('%d/%m/%y - %H:%M:%S')}")
        return embed

    # Set the starboard channel
    @app_commands.command(
        name='setchannel',
        description="Sets the Starboard channel."
    )
    @commands.has_role('bot manager')
    async def starboard_setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE serverdata SET starboard_channel=$2 WHERE guild_id=$1", interaction.guild.id, channel.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Starboard channel set.", ephemeral=False)

    # Set the starboard threshold
    @app_commands.command(
        name='setthreshold',
        description="Sets the Starboard threshold"
    )
    @commands.has_role('bot manager')
    async def starboard_setthreshold(self, interaction: discord.Interaction, threshold: int):
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE serverdata SET starboard_threshold=$2 WHERE guild_id=$1", interaction.guild.id, threshold)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            log.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Starboard threshold set.", ephemeral=False)

    # Add to starboard
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Parse payload
        guild = await self.bot.fetch_guild(payload.guild_id)
        channel = await guild.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        member = await guild.fetch_member(payload.user_id)
        emoji = payload.emoji.name

        # Reject embed messages
        if len(message.embeds) != 0:
            return

        # Get starboard channel
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT starboard_channel FROM serverdata WHERE guild_id=$1", guild.id)
                channel = await self.bot.fetch_channel(response[0]['starboard_channel'])
        except PostgresError as e:
            log.exception(e)
            return
        except AttributeError as e:
            log.exception(e)
        except discord.DiscordException as e:
            log.exception(e)

        # Get starboard threshold
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT starboard_threshold FROM serverdata WHERE guild_id=$1", guild.id)
                threshold = response[0]['starboard_threshold']
        except PostgresError as e:
            log.exception(e)
            return
        except AttributeError as e:
            log.exception(e)
            return

        # Logic
        if emoji == '🌟' and member.guild_permissions.administrator:
            embed = self.create_embed(message, member.name)
            await channel.send(embed=embed)
        elif emoji == '⭐':
            stars = 0

            # Get reactions
            for reaction in message.reactions:
                if reaction.emoji == '⭐':
                    stars += 1

            # Check and create
            if stars == threshold:
                embed = self.create_embed(message, f"{guild.name} Community")
                await channel.send(embed=embed)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(starboard(bot))