"""Welcome message functions"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "2.1.0"
__status__ = "Production"

# Standard library
from logging import getLogger

# Third-party
import discord
from discord.ext import commands
from discord import app_commands
from asyncpg.exceptions import PostgresError

# Internal
from start import CENBot

log = getLogger('CENBot.welcome')


class WelcomeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, bot: CENBot, current_channel_id: int | None) -> None:
        default_values = [discord.Object(id=current_channel_id)] if current_channel_id else []
        super().__init__(
            placeholder="Select a welcome channel...",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            default_values=default_values,
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        new_channel_id = self.values[0].id if self.values else None
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.welcome (guild_id, channel)
                                   VALUES ($1, $2)
                                   ON CONFLICT (guild_id) DO UPDATE SET channel=EXCLUDED.channel
                                   """, interaction.guild.id, new_channel_id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error saving the channel, please try again.", ephemeral=True)
            return

        if new_channel_id:
            await interaction.response.send_message(f"Welcome channel set to {self.values[0].mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("Welcome channel cleared.", ephemeral=True)


class WelcomeMessageModal(discord.ui.Modal, title="Welcome Message"):
    message = discord.ui.TextInput(
        label="Welcome Message",
        style=discord.TextStyle.paragraph,
        placeholder="Use <new_member> to mention the joining user.",
        required=False,
        max_length=1000,
    )

    def __init__(self, bot: CENBot, current_message: str | None) -> None:
        super().__init__()
        self.bot = bot
        if current_message:
            self.message.default = current_message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        new_message = self.message.value.strip() or None
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.welcome (guild_id, message)
                                   VALUES ($1, $2)
                                   ON CONFLICT (guild_id) DO UPDATE SET message=EXCLUDED.message
                                   """, interaction.guild.id, new_message)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error saving your message, please try again.", ephemeral=True)
            return

        await interaction.response.send_message("Welcome message saved.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.exception(error)
        await interaction.response.send_message("Something went wrong, please try again.", ephemeral=True)


class SetMessageButton(discord.ui.Button):
    def __init__(self, bot: CENBot, current_message: str | None) -> None:
        super().__init__(label="Set Message", style=discord.ButtonStyle.primary)
        self.bot = bot
        self.current_message = current_message

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(WelcomeMessageModal(self.bot, self.current_message))


class WelcomeConfigView(discord.ui.LayoutView):
    def __init__(self, bot: CENBot, current_channel_id: int | None, current_message: str | None) -> None:
        super().__init__()
        self.add_item(discord.ui.TextDisplay("**Welcome Channel**"))
        self.add_item(discord.ui.ActionRow(WelcomeChannelSelect(bot, current_channel_id)))
        self.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        self.add_item(discord.ui.TextDisplay("**Welcome Message**"))
        self.add_item(discord.ui.ActionRow(SetMessageButton(bot, current_message)))


@app_commands.guild_only()
class Welcome(commands.GroupCog, name='welcome'):
    """These are the welcome message functions."""
    def __init__(self, bot: CENBot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def enable(self, interaction: discord.Interaction) -> None:
        """Enables the welcome module.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET welcome_enabled=true
                                   WHERE id=$1
                                   """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Welcome module enabled.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def disable(self, interaction: discord.Interaction) -> None:
        """Disables the welcome module.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   UPDATE cenbot.guilds
                                   SET welcome_enabled=false
                                   WHERE id=$1
                                   """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("Welcome module disabled.", ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def configure(self, interaction: discord.Interaction) -> None:
        """Opens the welcome configuration view.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT channel, message
                                             FROM cenbot.welcome
                                             WHERE guild_id=$1
                                             """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching your settings, please try again.", ephemeral=True)
            return

        current_channel_id = record['channel'] if record else None
        current_message = record['message'] if record else None

        view = WelcomeConfigView(self.bot, current_channel_id, current_message)
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.checks.has_role("CENBot Admin")
    @app_commands.command()
    async def test_message(self, interaction: discord.Interaction) -> None:
        """Tests the welcome message regardless of enabled state.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT g.welcome_enabled, w.channel, w.message
                                             FROM cenbot.guilds g LEFT JOIN cenbot.welcome w ON g.id=w.guild_id
                                             WHERE g.id=$1
                                             """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again.", ephemeral=True)
            return

        if not record or not record['channel']:
            await interaction.response.send_message("No welcome channel configured. Use `/welcome configure` to set one.", ephemeral=True)
            return

        channel = self.bot.get_channel(record['channel'])
        if channel is None:
            await interaction.response.send_message("The configured welcome channel no longer exists.", ephemeral=True)
            return

        await channel.send(record['message'].replace('<new_member>', interaction.user.mention))
        note = " *(module is currently disabled)*" if not record['welcome_enabled'] else ""
        await interaction.response.send_message(f"Test sent.{note}", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Sends a welcome message on user join.

        :param member: the member who joined
        :type member: discord.Member
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("""
                                             SELECT g.welcome_enabled, w.channel, w.message
                                             FROM cenbot.guilds g LEFT JOIN cenbot.welcome w ON g.id=w.guild_id
                                             WHERE g.id=$1
                                             """, member.guild.id)
        except PostgresError as e:
            log.exception(e)
            return

        if record and record['welcome_enabled'] and record['channel']:
            channel = self.bot.get_channel(record['channel'])
            if channel:
                await channel.send(record['message'].replace('<new_member>', member.mention))


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Welcome(bot))
