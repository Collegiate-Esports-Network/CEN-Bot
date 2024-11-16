__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Setup Functions"""

# Python imports
import asyncpg

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
log = logging.getLogger('CENBot.quickstart')


class View_Setup(discord.ui.View):
    """Creates the modal for server setup
    """
    def __init__(self, db_pool: asyncpg.Pool) -> None:
        super().__init__(timeout=None)
        self.db_pool = db_pool

    # Welcome channel select
    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Welcome Channel")
    async def welcome_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect) -> None:
        # Create Modal
        class Modal(discord.ui.Modal):
            def __init__(self):
                super().__init__(timeout=None, title="Welcome Message")

            welcome_message = discord.ui.TextInput(label="Welcome Message", placeholder="Welcome to the server, <new_member>!", required=False, default=None)

            async def on_submit(self, interaction: discord.Interaction) -> None:
                # Send response
                await interaction.response.send_message("Welcome message recorded.", ephemeral=True)

                # Stop modal
                self.stop()

        # Initiate modal
        modal = Modal()

        # Send
        await interaction.response.send_modal(modal)

        # Wait for Modal to submit
        await modal.wait()

        # Get value back
        welcome_message = modal.welcome_message.value
        print(welcome_message)

    # Log channel select
    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Log Channel")
    async def log_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect) -> None:
        # Create view
        class View(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)

            # Create selector
            @discord.ui.select(cls=discord.ui.Select,
                                options=[
                                    discord.SelectOption(
                                        label="Log Level 1: Reports Only",
                                        value=1
                                    ),
                                    discord.SelectOption(
                                        default=True,
                                        label="Log Level 2: Message Edits (Default)",
                                        value=2
                                    ),
                                    discord.SelectOption(
                                        label="Log Level 3: All Message Activity",
                                        value=3
                                    ),
                                    discord.SelectOption(
                                        label="Log Level 4: All Member Activity",
                                        value=4
                                    ),
                                ],
                                placeholder="Log Level")
            async def log_level(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect) -> None:
                self.values = select.values

        # Initialize level selctor
        view = View()

        # Send level selector
        await interaction.response.send_message("**Log Level**", view=view)

        # Wait
        await view.wait()

        # Get value back
        level = view.values[0]
        print(level)

    # Report channel select
    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Report Channel")
    async def report_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect) -> None:
        return

    # Cancel button
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, row=4)
    async def cancel(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Responses submitted.", ephemeral=True)

        # Stop the view
        self.stop()

    # Submit button
    @discord.ui.button(label="Submit", style=discord.ButtonStyle.green, row=4)
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message(f"Button {button.label} pressed.", ephemeral=True)

        # Stop the view
        self.stop()


@app_commands.guild_only()
class quickstart(commands.Cog):
    """Server Quickstart commands
    """
    # Init
    def __init__(self, bot: cbot) -> None:
        self.bot = bot

    @app_commands.command(
        name='initialize',
        description="Initializes the server and sets up the bot"
    )
    @commands.has_guild_permissions(administrator=True)
    async def utility_setup(self, interaction: discord.Interaction) -> None:
        # Create bot manager role
        try:
            await interaction.guild.create_role(
                name="Bot Manager",
                permissions=discord.Permissions(administrator=True),
                color=discord.Color.from_str("#2AA58D"),
                reason="Required role for bot interaction"
            )
        except discord.Forbidden as e:
            log.exception(e)
            await interaction.response.send_message("I do not have the necessary permissions to auto-setup.", ephemeral=True)
            return
        except discord.HTTPException as e:
            log.exception(e)
            await interaction.response.send_message("There was an error creating the role, please try again.", ephemeral=True)
            return

        # Assign to user
        try:
            await interaction.user.add_roles(discord.utils.get(interaction.guild.roles, name="Bot Manager"))
        except:
            interaction.response.send_message("There was an error, please try again.", ephemeral=True)

        # Send modal
        await interaction.response.send_message("\n**Server Setup**", view=View_Setup(self.bot.db_pool), ephemeral=True)


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(quickstart(bot))