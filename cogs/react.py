__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Reaction role functions"""

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands


class react(commands.GroupCog, name='react'):
    """These are the reaction role functions
    """
    # Init
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()

    # Set reaction channel
    @app_commands.command(
        name='setchannel',
        description="Sets the reaction channel"
    )
    @commands.has_role('bot manager')
    async def react_setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        # Update react channel
        async with self.bot.pool.acquire() as con:
            await con.execute("UPDATE serverdata SET react_channel=$1 WHERE guild_id=$2", channel.id, interaction.guild.id,)

        # Respond
        await interaction.response.send_message("react channel saved", ephemeral=False)

    # Add reaction role
    @app_commands.command(
        name='update',
        description="Updates/adds a reaction role"
    )
    async def react_update(self, interaction: discord.Interaction) -> None:
        # Create role info modal
        class RoleInfo(discord.ui.Modal):
            def __init__(self, name: str) -> None:
                # Init
                self.__name = name
                super().__init__(title=f'Role Information for {self.__name}', timeout=60)

                # Creating modal fields
                self.category_name = discord.ui.TextInput(
                    label='Category Name',
                    style=discord.TextStyle.short,
                    max_length=256,
                    required=True
                )
                self.category_desc = discord.ui.TextInput(
                    label='Category Description',
                    style=discord.TextStyle.short,
                    max_length=1024,
                    required=False
                )
                self.role_desc = discord.ui.TextInput(
                    label='Role Description',
                    style=discord.TextStyle.short,
                    max_length=1024,
                    required=False
                )

                # Adding fields to modal
                self.add_item(self.category_name)
                self.add_item(self.category_desc)
                self.add_item(self.role_desc)

            async def on_submit(self, interaction: discord.Interaction) -> None:
                self.category_name = self.category_name.value
                self.category_desc = self.category_desc.value
                self.role_desc = self.role_desc.value
                await interaction.response.send_message(f"Information for {self.__name} added", ephemeral=True, delete_after=5.0)

        # Create role selector
        class SelectRole(discord.ui.RoleSelect):
            def __init__(self) -> None:
                super().__init__(placeholder='Choose a role', min_values=1, max_values=1)

            async def callback(self, interaction: discord.Interaction) -> None:
                self.name = self.values[0].name
                self.id = self.values[0].id
                self.info = RoleInfo(self.name)
                await interaction.response.send_modal(self.info)

        # Create emoji selector
        class SelectEmoji(discord.ui.Select):
            def __init__(self, guild: discord.Guild) -> None:
                super().__init__(placeholder='Choose an emoji or the role above', min_values=1, max_values=1)
                for emoji in guild.emojis:
                    self.add_option(label=emoji.name, emoji=emoji, value=emoji.id)

            async def callback(self, interaction: discord.Interaction) -> None:
                self.id = self.values[0]
                await interaction.response.send_message("Your data has been recorded", ephemeral=True, delete_after=5.0)

        # Send role selector
        class view(discord.ui.View):
            def __init__(self, guild: discord.Guild) -> None:
                # Init classes
                self.role_emoji = SelectEmoji(guild)
                self.role = SelectRole()
                super().__init__(timeout=70)

                # Add items
                self.add_item(self.role)
                self.add_item(self.role_emoji)

        # Send view
        role_info = view(interaction.guild)
        await interaction.response.send_message(view=role_info, ephemeral=True)

        # Wait for timeout
        await role_info.wait()

        # Edit message
        await interaction.edit_original_response(content="This view has timed out")

        # Get data and add to DataBase
        print(role_info.role.info.category_name, role_info.role.info.category_desc)
        print(role_info.role.name, role_info.role.id, role_info.role.info.role_desc, role_info.role_emoji.id)


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(react(bot))