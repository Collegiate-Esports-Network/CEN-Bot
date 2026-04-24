"""XP functions"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "3"
__status__ = "Production"

# Standard library
import random
from logging import getLogger

# Third-party
import discord
from discord.ext import commands
from discord import app_commands
from asyncpg.exceptions import PostgresError

# Internal
from start import CENBot
from utils.embeds import requester_footer

log = getLogger('CENBot.xp')


@app_commands.guild_only()
class XP(commands.GroupCog, name='xp'):
    """These are all functions related to the xp system of the bot."""
    def __init__(self, bot: CENBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        """Award XP on every non-bot, non-DM message.

        XP is awarded probabilistically: 70% chance of 1 XP, 20% chance of 2,
        and 10% chance of 3 per message.

        :param msg: the incoming message
        :type msg: discord.Message
        """
        if self.bot.user == msg.author:
            return
        if msg.channel.type == discord.ChannelType.private:
            return

        num = random.randint(1, 100)
        if num < 70:
            exp = 1
        elif num < 90:
            exp = 2
        else:
            exp = 3

        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("""
                                  UPDATE public.profiles
                                  SET message_xp = COALESCE(message_xp, 0) + $1
                                  WHERE discord_id = $2
                                  """, exp, msg.author.id)
        except PostgresError as e:
            log.exception(e)

    @app_commands.command(
        name='xp',
        description="Returns your current xp."
    )
    async def xp_xp(self, interaction: discord.Interaction) -> None:
        """Return the calling user's current total XP.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as con:
                record = await con.fetchrow(
                    "SELECT message_xp FROM public.profiles WHERE discord_id = $1",
                    interaction.user.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again.", ephemeral=True)
            return

        if record is None:
            await interaction.response.send_message("You don't have a CEN profile linked to your Discord account.", ephemeral=True)
        elif record['message_xp'] is None:
            await interaction.response.send_message("You haven't earned any XP yet.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Your xp is: {record['message_xp']}.", ephemeral=True)

    @app_commands.command(
        name='leaderboard',
        description="Returns the top 20 xp leaders."
    )
    async def xp_leaderboard(self, interaction: discord.Interaction) -> None:
        """Display the top 20 users by XP across all guilds.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as con:
                records = await con.fetch("""
                                          SELECT discord_id, message_xp FROM public.profiles
                                          WHERE message_xp > 0 ORDER BY message_xp DESC LIMIT 20
                                          """)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching the leaderboard, please try again.", ephemeral=True)
            return

        embed = discord.Embed(title='Top 20 xp Leaders')

        text = "```\n"
        i = 1
        for row in records:
            member = self.bot.get_user(int(row['discord_id']))
            if member is not None:
                text += f"#{i}: {member.display_name} - {row['message_xp']}\n"
                i += 1
        text += "```"
        embed.add_field(name="", value=text, inline=False)

        requester_footer(embed, interaction)
        await interaction.response.send_message(embed=embed, ephemeral=False)


async def setup(bot: CENBot) -> None:
    await bot.add_cog(XP(bot))
