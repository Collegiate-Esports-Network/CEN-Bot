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
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("React channel saved.", ephemeral=False)

    @app_commands.command(
        name='update',
        description="Updates/Adds/Deletes react information"
    )
    @commands.has_role('bot manager')
    async def react_update(self, interaction: discord.Interaction) -> None:
        # Create category addition modal
        class Category_add(discord.ui.Modal):
            def __init__(self):
                super().__init__(title='Category Additon Form', timeout=60.0)

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

            async def on_submit(self, interaction: discord.Interaction) -> None:
                self.name = self.name.value
                self.desc = self.desc.value
                await interaction.response.send_message("Processing...", ephemeral=True, delete_after=1.0)
                self.stop()

        # Create category deletion modal
        class Category_delete(discord.ui.Modal):
            def __init__(self):
                super().__init__(title='Category Deletion Form', timeout=10.0)

                # Create modal items
                self.name = discord.ui.TextInput(
                    label='Category Name',
                    style=discord.TextStyle.short,
                    placeholder='Type here',
                    required=True
                )

                # Add item
                self.add_item(self.name)

            async def on_submit(self, interaction: discord.Interaction) -> None:
                self.name = self.name.value
                await interaction.response.send_message("Processing...", ephemeral=True, delete_after=1.0)
                self.stop()

        # Create role info modal
        class RoleInfo(discord.ui.Modal):
            def __init__(self):
                super().__init__(title='Role Information', timeout=60.0)

                # Create modal items
                self.category = discord.ui.TextInput(
                    label='Category Name',
                    style=discord.TextStyle.short,
                    placeholder='Type here',
                    required=True
                )
                self.desc = discord.ui.TextInput(
                    label='Role Description',
                    style=discord.TextStyle.short,
                    placeholder='Type here',
                    required=False
                )

                # Add items
                self.add_item(self.category)
                self.add_item(self.desc)

            async def on_submit(self, interaction: discord.Interaction) -> None:
                self.category = self.category.value
                self.desc = self.desc.value
                await interaction.response.defer()
                self.stop()

        # Create role addition view
        class RoleView_add(discord.ui.View):
            def __init__(self, guild: discord.Guild):
                super().__init__(timeout=20.0)

                # Create role selector
                class RoleSelect(discord.ui.RoleSelect):
                    def __init__(self):
                        super().__init__(placeholder='Choose a role', min_values=1, max_values=1)

                    async def callback(self, interaction: discord.Interaction) -> None:
                        self.name = self.values[0].name
                        self.id = self.values[0].id
                        self.info = RoleInfo()
                        await interaction.response.send_modal(self.info)

                # Create emoji selector
                class EmojiSelect(discord.ui.Select):
                    def __init__(self, guild: discord.Guild):
                        super().__init__(placeholder='Choose an emoji', min_values=1, max_values=1)
                        for emoji in guild.emojis:
                            self.add_option(label=emoji.name, emoji=emoji, value=emoji.id)

                    async def callback(self, interaction: discord.Interaction) -> None:
                        self.id = self.values[0]
                        await interaction.response.send_message("Processing...", ephemeral=True, delete_after=1.0)

                # Init classes
                self.role = RoleSelect()
                self.emoji = EmojiSelect(guild)

                # Add items
                self.add_item(self.role)
                self.add_item(self.emoji)

        # Create role deletion view
        class RoleView_delete(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=20.0)

                class RoleSelect(discord.ui.RoleSelect):
                    def __init__(self):
                        super().__init__(placeholder='Choose a role', min_values=1, max_values=1)

                    async def callback(self, interaction: discord.Interaction) -> None:
                        self.id = self.values[0].id
                        await interaction.response.send_message("Processing...", ephemeral=True, delete_after=1.0)

                # Init classes
                self.role = RoleSelect()

                # Add items
                self.add_item(self.role)

        # Create view
        class View(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=1200)  # 20 minute timeout

            @discord.ui.button(label='Update/Add a category', style=discord.ButtonStyle.green, row=0)
            async def send_categoryinfo(self, interaction: discord.Interaction, button: discord.ui.Button):
                category_info = Category_add()
                await interaction.response.send_modal(category_info)
                await category_info.wait()

                # Verify data
                self.name = category_info.name
                self.desc = category_info.desc

            @discord.ui.button(label='Delete a category', style=discord.ButtonStyle.red, row=0)
            async def send_deletecategory(self, interaction: discord.Interaction, buttoon: discord.ui.Button):
                category_info = Category_delete()
                await interaction.response.send_modal(category_info)
                await category_info.wait()

                # Verify data
                self.name = category_info.name

            @discord.ui.button(label='Update/Add a role', style=discord.ButtonStyle.green, row=1)
            async def send_roleinfo(self, interaction: discord.Interaction, button: discord.ui.Button):
                role_info = RoleView_add(interaction.guild)
                await interaction.response.send_message(view=role_info, ephemeral=True)
                await role_info.wait()

                # Verify data
                self.name = role_info.role.name
                self.id = role_info.role.id
                self.desc = role_info.role.info.desc
                self.emoji_id = role_info.emoji.id

            @discord.ui.button(label='Delete a role', style=discord.ButtonStyle.red, row=1)
            async def send_deleterole(self, interaction: discord.Interaction, button: discord.ui.Button):
                role_info = RoleView_delete()
                await interaction.response.send_message(view=role_info, ephemeral=True)
                await role_info.wait()

                # Verify data
                self.role_id = role_info.id

        # Send view
        view = View()
        await interaction.response.send_message(view=view, ephemeral=True)

        # Wait
        await view.wait()
        await interaction.edit_original_response(content="This view has timed out.")

        # Upsert info
        # try:
        #     async with self.bot.pool.acquire() as con:
        #         await con.execute("INSERT INTO react_cat (category_name, category_desc, guild_id) \
        #                           VALUES ($1, $2, $3) ON CONFLICT \
        #                           UPDATE react_cat SET (category_desc=$2) WHERE category_name=$1 AND guild_id=$3",
        #                           category_info.name, category_info.desc, interaction.guild.id)
        # except PostgresError as e:
        #     logger.exception(e)
        #     await interaction.edit_original_response(content="There was an error upserting your data, please try again.", view=None)
        # except Exception as e:
        #     logger.exception(e)
        #     await interaction.edit_original_response(content="There was an error, please try again.", view=None)
        # else:
        #     await interaction.edit_original_response(content="Category updated.", view=None)


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(react(bot))