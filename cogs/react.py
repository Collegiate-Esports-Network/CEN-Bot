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

# Logging
import logging
from asyncpg.exceptions import PostgresError
logger = logging.getLogger('react')


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
        try:
            async with self.bot.pool.acquire() as con:
                await con.execute("UPDATE serverdata SET react_channel=$1 WHERE guild_id=$2", channel.id, interaction.guild.id,)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("React channel saved.", ephemeral=False)

    @app_commands.command(
        name='updatecategory',
        description="Updates/adds a category"
    )
    @commands.has_role('bot manager')
    async def react_updatecategory(self, interaction: discord.Interaction) -> None:
        # Create category info modal
        class CategoryInfo(discord.ui.Modal):
            def __init__(self):
                super().__init__(title='Category Information', timeout=60)

                # Create modal items
                self.name = discord.ui.TextInput(
                    label='Category Name',
                    style=discord.TextStyle.short,
                    placeholder='Type here',
                    required=True
                )
                self.desc = discord.ui.TextInput(
                    label='Category Description',
                    style=discord.TextStyle.short,
                    placeholder='Type here',
                    required=False
                )

                # Add items
                self.add_item(self.name)
                self.add_item(self.desc)

            async def on_submit(self, interaction: discord.Interaction, /) -> None:
                self.name = self.name.value
                self.desc = self.desc.value
                await interaction.response.send_message("Information recorded.", ephemeral=True, delete_after=5.0)
                self.stop()

        category_info = CategoryInfo()

        # Create category info view
        class CategoryView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=70)
                self.name = None
                self.desc = None

            @discord.ui.button(label='Get Form', style=discord.ButtonStyle.grey, row=0)
            async def send_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_modal(category_info)
                await category_info.wait()
                self.name = category_info.name
                self.desc = category_info.desc

            @discord.ui.button(label='Submit', style=discord.ButtonStyle.green, row=1)
            async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_message('Submitting...', ephemeral=True, delete_after=5.0)
                self.stop()

            async def on_timeout(self) -> None:
                await interaction.resp

        # Send view
        category_view = CategoryView()
        await interaction.response.send_message(view=category_view, ephemeral=True)

        # Wait
        await category_view.wait()
        await interaction.edit_original_response(content="This view has timed out.")

        # Upsert info
        try:
            async with self.bot.pool.acquire() as con:
                await con.execute("INSERT INTO react_cat (category_name, category_desc, guild_id) \
                                  VALUES ($1, $2, $3) ON CONFLICT \
                                  UPDATE react_cat SET (category_desc=$2) WHERE category_name=$1 AND guild_id=$3",
                                  category_info.name, category_info.desc, interaction.guild.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.edit_original_response(content="There was an error upserting your data, please try again.", view=None)
        except Exception as e:
            logger.exception(e)
            await interaction.edit_original_response(content="There was an error, please try again.", view=None)
        else:
            await interaction.edit_original_response(content="Category updated.", view=None)

    @app_commands.command(
        name='removecategory',
        description="Removes a category"
    )
    async def react_removecategory(self, interaction: discord.Interaction) -> None:
        # Get all categories
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("SELECT * FROM react_cat WHERE guild_id=$1", interaction.guild.id)
            response = dict(response)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error retrieving your categories, please try again.", ephemeral=True)
            return
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            return

        # Create select options
        print(response)

    # Add reaction role
    @app_commands.command(
        name='update',
        description="Adds a reaction category"
    )
    @commands.has_role('bot manager')
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
                await interaction.response.send_message(f"Information for {self.__name} added.", ephemeral=True, delete_after=5.0)

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
                await interaction.response.send_message("Your data has been recorded.", ephemeral=True, delete_after=5.0)

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
        await interaction.edit_original_response(content="This view has timed out.")

        # Rip data and add to database
        try:
            role_id = role_info.role.id
            role_name = role_info.role.name
            role_desc = role_info.role.info.role_desc
            role_emoji_id = role_info.role_emoji.id
            category_name = role_info.role.info.category_name
            category_desc = role_info.role.info.category_desc
            async with self.bot.pool.acquire() as con:
                await con.execute("INSERT INTO react (role_id, role_name, role_desc, role_emoji_id, category_name, category_desc, guild_id) \
                                  VALUES ($1, $2, $3, $4, $5, $6, $7) ON CONFLICT \
                                  UPDATE SET role_desc=$3, role_emoji_id=$4, category_name=$5, category_desc=$6 WHERE role_id=$1",
                                  role_id, role_name, role_desc, role_emoji_id, category_name, category_desc, interaction.guild.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.edit_original_response(content="There was an error inserting/updating your data, \
                                                              please try again later.", view=None)
        except Exception as e:
            logger.exception(e)
            await interaction.edit_original_response(content="There was an error, please try again later.", view=None)
        else:
            await interaction.edit_original_response(content="The reaction was updated.", view=None)

    # Remove reaction role
    @app_commands.command(
        name='remove',
        description="Removes a reaction role"
    )
    @app_commands.describe(
        role="The role mention"
    )
    @commands.has_role('bot manager')
    async def react_remove(self, interaction: discord.Interaction, role: discord.Role) -> None:
        try:
            async with self.bot.pool.acquire() as con:
                await con.execute("DELETE FROM react WHERE role_id=$1", role.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error deleting your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("The reaction was removed.", ephemeral=True)

    @app_commands.command(
        name='send',
        description="Sends the reaction embeds"
    )
    @commands.has_role('bot manager')
    async def react_send(self, interaction: discord.Interaction) -> None:
        # Get roles
        try:
            async with self.bot.pool.acquire() as con:
                reactions = await con.execute("SELECT * FROM react WHERE guild_id=$1", interaction.guild.id)
        except Exception:
            interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            return


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(react(bot))