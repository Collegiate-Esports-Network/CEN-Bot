__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "3.0.0"
__status__ = "Production"
__doc__ = """Utility Functions"""

# Python imports
import sys
from time import time
import random
import asyncpg

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Logging
import logging
log = logging.getLogger('CENBot.utility')


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
class utility(commands.Cog):
    """Simple commands for all.
    """
    # Init
    def __init__(self, bot: cbot) -> None:
        self.bot = bot

    @app_commands.command(
        name='ping',
        description="Replies with Pong! (and the bots ping)",
    )
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! ({round(self.bot.latency * 1000, 4)} ms)", ephemeral=True)

    @app_commands.command(
        name='about',
        description="Returns the current bot information",
    )
    async def about(self, interaction: discord.Interaction) -> None:
        # Create embed
        embed = discord.Embed(title='Bot Info', description="Here is the most up-to-date information on the bot.", color=0x2374A5)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        embed.add_field(name="Bot Version:", value=self.bot.version)
        embed.add_field(name="Python Version:", value=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        embed.add_field(name="Discord.py Version:", value=discord.__version__)
        embed.add_field(name="Written By:", value="[Justin Panchula](https://github.com/JustinPanchula), and [Chris Taylor](https://github.com/Taylo5ce)", inline=False)
        embed.add_field(name="Server Information:", value=f"This bot is in {len(self.bot.guilds)} servers watching over \
                                                            {len(set(self.bot.get_all_members()))-len(self.bot.guilds)} members.", inline=False)
        embed.set_footer(text=f"Information requested by: {interaction.user}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name='setup',
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

    @app_commands.command(
        name='flip',
        description="Flips a coin"
    )
    async def flip(self, interaction: discord.Interaction) -> None:
        # Choose heads or tails
        random.seed(round(time() * 1000))
        heads = random.randint(0, 1)

        if heads:
            await interaction.response.send_message(f"{interaction.user.mention} the coin is Heads.")
        else:
            await interaction.response.send_message(f"{interaction.user.mention} the coin is Tails.")


# Add to bot
async def setup(bot: cbot) -> None:
    await bot.add_cog(utility(bot))
