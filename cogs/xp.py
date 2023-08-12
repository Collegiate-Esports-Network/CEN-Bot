__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """xp Functions"""

# Python imports
import random
from time import time

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
        if self.bot.user == ctx.author:
            return

        # Generate random number between 1 and 100 and assign xp
        random.seed(round(time() * 1000))
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
            async with self.bot.db_pool.acquire() as con:
                record = await con.fetch(f"SELECT s_{ctx.guild.id} FROM xp WHERE user_id=$1", ctx.author.id)
            record = dict(record[0])
        except PostgresError as e:
            logger.exception(e)
        except IndexError:
            # Add user to table
            try:
                async with self.bot.db_pool.acquire() as con:
                    await con.execute("INSERT INTO xp (user_id) VALUES ($1)", ctx.author.id)
            except PostgresError as e:
                logger.exception(e)
        else:
            old_exp = record[f's_{ctx.guild.id}']
            # Add change in xp
            new_exp = old_exp + exp
            try:
                async with self.bot.db_pool.acquire() as con:
                    await con.execute(f"UPDATE xp SET s_{ctx.guild.id}=$1 WHERE user_id=$2", new_exp, ctx.author.id)
            except PostgresError as e:
                logger.exception(e)
                return

    @app_commands.command(
        name='xp',
        description="Returns your current xp."
    )
    async def xp_xp(self, interaction: discord.Interaction) -> None:
        # Get xp records
        try:
            async with self.bot.db_pool.acquire() as con:
                record = await con.fetch(f"SELECT s_{interaction.guild.id} FROM xp WHERE user_id=$1", interaction.user.id)
            record = dict(record[0])
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again.", ephemeral=True)
            return

        # Record check
        try:
            exp = record[f's_{interaction.guild.id}']
        except KeyError as e:
            logger.exception(e)
            await interaction.response.send_message("You haven't talked in this server yet.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Your xp in this server is: {exp}.", ephemeral=True)

    @app_commands.command(
        name='leaderboard',
        description="Returns the top 20 xp leaders."
    )
    async def xp_leaderboard(self, interaction: discord.Interaction) -> None:
        # Get xp data
        try:
            async with self.bot.db_pool.acquire() as con:
                record = await con.fetch(f"SELECT (user_id, s_{interaction.guild.id}) FROM xp")
            temp_records = []
            for r in record:
                temp_records.append(dict(r)['row'])
            record = dict(temp_records)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error fetching the leaderboard, please try again.", ephemeral=True)
            return

        # Init embed
        embed = discord.Embed(title='Top 20 xp Leaders')

        # Sort record in descending order
        record = dict(sorted(record.items(), key=lambda x: x[1], reverse=True))

        # Fill embed
        text = "```\n"
        i = 1
        for user_id, exp in record.items():
            member = self.bot.get_user(user_id)
            if member is not None and exp != 0:
                text += f"#{i}: {member.display_name} - {exp}\n"

                # Increment 1
                i += 1
            # Keep list at Top 20
            if i > 20:
                break
        text += "```"
        embed.add_field(name="", value=text, inline=False)

        # Send response
        await interaction.response.send_message(embed=embed, ephemeral=False)

    # Sync the xp
    @app_commands.command(
        name='sync',
        description='Syncs xp servers with servers the bot is currently in. To be used only when restarting'
    )
    @commands.has_role('bot manager')
    async def xp_sync(self, interaction: discord.Interaction):
        for guild in self.bot.guilds:
            try:
                async with self.bot.db_pool.acquire() as con:
                    await con.execute(f"ALTER TABLE xp ADD COLUMN IF NOT EXISTS s_{guild.id} INT NOT NULL DEFAULT 0")
            except PostgresError as e:
                logger.exception(e)
                await interaction.response.send_message("There was an error syncing the xp table, please try again.", ephemeral=True)

        # Send response
        await interaction.response.send_message("The xp servers were synced succesfully.", ephemeral=False)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(xp(bot))