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
    """Saves the chosen text channel as the guild's welcome channel."""

    def __init__(self, bot: CENBot, current_channel_id: int | None) -> None:
        """Initialise with the currently configured channel pre-selected.

        :param bot: the bot instance
        :type bot: CENBot
        :param current_channel_id: the ID of the currently set channel, or ``None``
        :type current_channel_id: int | None
        """
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
        """Persist the selected channel and confirm to the user.

        :param interaction: the discord interaction triggered by the select
        :type interaction: discord.Interaction
        """
        new_channel_id = self.values[0].id if self.values else None
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.guilds (id, welcome_channel)
                                   VALUES ($1, $2)
                                   ON CONFLICT (id) DO UPDATE SET welcome_channel=EXCLUDED.welcome_channel
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
    """Modal for entering or editing the guild's welcome message text.

    Use ``<new_member>`` as a placeholder that is replaced with the joining
    member's mention at send time.
    """

    message = discord.ui.TextInput(
        label="Welcome Message",
        style=discord.TextStyle.paragraph,
        placeholder="Use <new_member> to mention the joining user.",
        required=False,
        max_length=1000,
    )

    def __init__(self, bot: CENBot, current_message: str | None) -> None:
        """Initialise the modal, pre-filling the text input if a message already exists.

        :param bot: the bot instance
        :type bot: CENBot
        :param current_message: the existing welcome message text, or ``None``
        :type current_message: str | None
        """
        super().__init__()
        self.bot = bot
        if current_message:
            self.message.default = current_message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Persist the submitted welcome message text.

        :param interaction: the discord interaction triggered by modal submission
        :type interaction: discord.Interaction
        """
        new_message = self.message.value.strip() or None
        try:
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                   INSERT INTO cenbot.guilds (id, welcome_message)
                                   VALUES ($1, $2)
                                   ON CONFLICT (id) DO UPDATE SET welcome_message=EXCLUDED.welcome_message
                                   """, interaction.guild.id, new_message)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error saving your message, please try again.", ephemeral=True)
            return

        await interaction.response.send_message("Welcome message saved.", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Log unexpected modal errors and notify the user.

        :param interaction: the discord interaction
        :type interaction: discord.Interaction
        :param error: the exception that was raised
        :type error: Exception
        """
        log.exception(error)
        await interaction.response.send_message("Something went wrong, please try again.", ephemeral=True)


class SetMessageButton(discord.ui.Button):
    """Button that opens the :class:`WelcomeMessageModal` for editing the welcome message."""

    def __init__(self, bot: CENBot, current_message: str | None) -> None:
        """Initialise the button, storing the current message for pre-filling the modal.

        :param bot: the bot instance
        :type bot: CENBot
        :param current_message: the existing welcome message text, or ``None``
        :type current_message: str | None
        """
        super().__init__(label="Set Message", style=discord.ButtonStyle.primary)
        self.bot = bot
        self.current_message = current_message

    async def callback(self, interaction: discord.Interaction) -> None:
        """Open the welcome message modal on button press.

        :param interaction: the discord interaction triggered by the button
        :type interaction: discord.Interaction
        """
        await interaction.response.send_modal(WelcomeMessageModal(self.bot, self.current_message))


class WelcomeConfigView(discord.ui.LayoutView):
    """Layout view combining the channel select and message button into one config panel."""

    def __init__(self, bot: CENBot, current_channel_id: int | None, current_message: str | None) -> None:
        """Build the config panel with current settings pre-populated.

        :param bot: the bot instance
        :type bot: CENBot
        :param current_channel_id: the ID of the currently set welcome channel, or ``None``
        :type current_channel_id: int | None
        :param current_message: the currently set welcome message text, or ``None``
        :type current_message: str | None
        """
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
                                             SELECT welcome_channel, welcome_message
                                             FROM cenbot.guilds
                                             WHERE id=$1
                                             """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching your settings, please try again.", ephemeral=True)
            return

        current_channel_id = record['welcome_channel'] if record else None
        current_message = record['welcome_message'] if record else None

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
                                             SELECT welcome_channel, welcome_message, welcome_enabled
                                             FROM cenbot.guilds
                                             WHERE id=$1
                                             """, interaction.guild.id)
        except PostgresError as e:
            log.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again.", ephemeral=True)
            return

        if not record or not record['welcome_channel']:
            await interaction.response.send_message("No welcome channel configured. Use `/welcome configure` to set one.", ephemeral=True)
            return

        channel = self.bot.get_channel(record['welcome_channel'])
        if channel is None:
            await interaction.response.send_message("The configured welcome channel no longer exists.", ephemeral=True)
            return

        await channel.send(record['welcome_message'].replace('<new_member>', interaction.user.mention))
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
                                             SELECT welcome_channel, welcome_message, welcome_enabled
                                             FROM cenbot.guilds
                                             WHERE id=$1
                                             """, member.guild.id)
        except PostgresError as e:
            log.exception(e)
            return

        if record and record['welcome_enabled'] and record['welcome_channel']:
            channel = self.bot.get_channel(record['welcome_channel'])
            if channel:
                await channel.send(record['welcome_message'].replace('<new_member>', member.mention))


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Welcome(bot))
