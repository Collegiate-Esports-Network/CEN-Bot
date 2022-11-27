__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """xp Functions"""

# Python imports
import random
import time
from collections import Counter

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
from asyncpg.exceptions import PostgresError
logger = logging.getLogger('xp')


class xp(commands.GroupCog, name='xp'):
    """ These are all functions related to the xp function of the bot.
    """
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_message(self, ctx: discord.Message) -> None:
        # Ignore messages from test server
        if self.bot.user == ctx.author or ctx.guild.id == 0:  # 778306842265911296
            return

        # Generate random number between 1 and 100 and assign xp
        random.seed(round(time.time() * 1000))
        num = random.randint(1, 100)
        exp = 0
        if num < 70:
            exp = 1
        elif num < 90:
            exp = 2
        else:
            exp = 3

        # Get xp records
        try:
            async with self.bot.pool.acquire() as con:
                record = await con.fetch("SELECT * FROM xp WHERE guild_id=$1", ctx.guild.id)
            record = dict(record[0])
        except PostgresError as e:
            logger.exception(e)
            return

        # Record check
        try:
            old_exp = record[f'm_{ctx.author.id}']
        except KeyError:
            # Add user to table
            try:
                async with self.bot.pool.acquire() as con:
                    await con.execute(f"ALTER TABLE xp ADD m_{ctx.author.id} int DEFAULT 0")
            except PostgresError as e:
                logger.exception(e)
                return
        else:
            # Add change in xp
            new_exp = old_exp + exp
            try:
                async with self.bot.pool.acquire() as con:
                    await con.execute(f"UPDATE xp SET m_{ctx.author.id}=$1 WHERE guild_id=$2", new_exp, ctx.guild.id)
            except PostgresError as e:
                logger.exception(e)
                return

    @app_commands.command(
        name='xp',
        description="Returns your current xp"
    )
    async def xp_xp(self, interaction: discord.Interaction) -> None:
        # Get xp records
        try:
            async with self.bot.pool.acquire() as con:
                record = await con.fetch("SELECT * FROM xp WHERE guild_id=$1", interaction.guild.id)
            record = dict(record[0])
        except PostgresError as e:
            logger.exception(e)
            interaction.response.send_message("There was an error fetching your data, please try again.", ephemeral=True)

        # Record check
        try:
            exp = record[f'm_{interaction.user.id}']
        except KeyError as e:
            logger.exception(e)
            await interaction.response.send_message("You haven't talked in this server yet.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Your xp in this server is: {exp}.", ephemeral=True)

    @app_commands.command(
        name='leaderboard',
        description="Returns the top 20 xp leaders"
    )
    async def xp_leaderboard(self, interaction: discord.Interaction) -> None:
        # Get xp data
        try:
            async with self.bot.pool.acquire() as con:
                record = await con.fetch("SELECT * FROM xp WHERE guild_id=$1", interaction.guild.id)
            record = dict(record[0])
        except PostgresError as e:
            logger.exception(e)
            interaction.response.send_message("There was an error fetching the leaderboard, please try again.", ephemeral=True)
            return

        # Remove guild from record
        record.pop('guild_id')

        # Init embed
        embed = discord.Embed(title='Top 20 xp Leaders')

        # Get top 20
        t20 = Counter(record)
        t20 = t20.most_common()
        i = 1
        for key, exp in t20:
            # Convert to int
            id = int(key[2:])

            # Build embed
            member = self.bot.get_user(id)
            embed.add_field(name=f"#{i}", value=f"{member.display_name} - xp: {exp}", inline=False)

            # Increment 1
            i += i

        # Send response
        await interaction.response.send_message(embed=embed, ephemeral=False)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(xp(bot))