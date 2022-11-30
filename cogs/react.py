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
        # Get reaction data
        try:
            async with self.bot.pool.acquire() as con:
                response = await con.fetch("Select react_data FROM serverdata WHERE guild_id=$1", interaction.guild.id)
            react_data = response[0]['react_data']
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again.", ephemeral=True)
            return
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            return

        # Create if empty
        if react_data is None:
            react_data = dict()

        # Create category addition modal
        class Category_add(discord.ui.Modal):
            def __init__(self):
                super().__init__(title='Category Additon Form', timeout=30.0)

                # Create modal items
                self.category = discord.ui.TextInput(
                    label='Category Name',
                    style=discord.TextStyle.short,
                    placeholder='Type here',
                    required=True
                )
                self.category_desc = discord.ui.TextInput(
                    label='Category Description',
                    style=discord.TextStyle.short,
                    placeholder='Type here',
                    required=False
                )

                # Add items
                self.add_item(self.category)
                self.add_item(self.category_desc)

            async def on_submit(self, interaction: discord.Interaction) -> None:
                self.category = self.category.value
                self.category_desc = self.category_desc.value
                await interaction.response.send_message("Processing...", ephemeral=True, delete_after=1.0)
                self.stop()

        # Create category deletion modal
        class Category_delete(discord.ui.Modal):
            def __init__(self):
                super().__init__(title='Category Deletion Form', timeout=10.0)

                # Create modal items
                self.category = discord.ui.TextInput(
                    label='Category Name',
                    style=discord.TextStyle.short,
                    placeholder='Type here',
                    required=True
                )

                # Add item
                self.add_item(self.category)

            async def on_submit(self, interaction: discord.Interaction) -> None:
                self.category = self.category.value
                await interaction.response.send_message("Processing...", ephemeral=True, delete_after=1.0)
                self.stop()

        # Create role addition view
        class RoleView_add(discord.ui.View):
            def __init__(self, guild: discord.Guild):
                super().__init__(timeout=20.0)

                # Create role info modal
                class Info(discord.ui.Modal):
                    def __init__(self):
                        super().__init__(title='Role Information', timeout=60.0)

                        # Create modal items
                        self.category = discord.ui.TextInput(
                            label='Category Name',
                            style=discord.TextStyle.short,
                            placeholder='Type here',
                            required=True
                        )
                        self.role_desc = discord.ui.TextInput(
                            label='Role Description',
                            style=discord.TextStyle.short,
                            placeholder='Type here',
                            required=False
                        )

                        # Add items
                        self.add_item(self.category)
                        self.add_item(self.role_desc)

                    async def on_submit(self, interaction: discord.Interaction) -> None:
                        self.category = self.category.value
                        self.role_desc = self.role_desc.value
                        await interaction.response.defer()
                        self.stop()

                # Create role selector
                class RoleSelect(discord.ui.RoleSelect):
                    def __init__(self):
                        super().__init__(placeholder='Choose a role', min_values=1, max_values=1)

                    async def callback(self, interaction: discord.Interaction) -> None:
                        self.role_name = self.values[0].name
                        self.role_id = self.values[0].id
                        self.info = Info()
                        await interaction.response.send_modal(self.info)

                # Create emoji selector
                class EmojiSelect(discord.ui.Select):
                    def __init__(self, guild: discord.Guild):
                        super().__init__(placeholder='Choose an emoji', min_values=1, max_values=1)
                        for emoji in guild.emojis:
                            self.add_option(label=emoji.name, emoji=emoji, value=emoji.id)

                    async def callback(self, interaction: discord.Interaction) -> None:
                        self.emoji_id = self.values[0]
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

                        # Add items
                        self.add_item(self.category)

                    async def on_submit(self, interaction: discord.Interaction) -> None:
                        self.category = self.category.value
                        await interaction.response.send_message("Processing...", ephemeral=True, delete_after=1.0)
                        self.stop()

                class RoleSelect(discord.ui.RoleSelect):
                    def __init__(self):
                        super().__init__(placeholder='Choose a role', min_values=1, max_values=1)

                    async def callback(self, interaction: discord.Interaction) -> None:
                        self.id = self.values[0].id
                        self.info = RoleInfo()
                        await interaction.response.send_modal(self.info)

                # Init classes
                self.role = RoleSelect()

                # Add items
                self.add_item(self.role)

        # Create view
        class View(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=40.0)  # 20 minute timeout (1200 sec)

            @discord.ui.button(label='Update/Add a category', style=discord.ButtonStyle.green, row=0)
            async def send_updatecategory(self, interaction: discord.Interaction, button: discord.ui.Button):
                category_info = Category_add()
                await interaction.response.send_modal(category_info)
                await category_info.wait()

                # Rip data
                category = category_info.category
                category_desc = category_info.category_desc

                # Update dict
                try:
                    react_data[category]['Description'] = category_desc
                except KeyError:
                    react_data[category] = {}
                    react_data[category]['Description'] = category_desc
                    react_data[category]['Roles'] = {}
                    react_data[category]['Embed_ID'] = None

            @discord.ui.button(label='Delete a category', style=discord.ButtonStyle.red, row=0)
            async def send_deletecategory(self, interaction: discord.Interaction, button: discord.ui.Button):
                category_info = Category_delete()
                await interaction.response.send_modal(category_info)
                await category_info.wait()

                # Rip data
                category = category_info.category

                # Remove from dict
                try:
                    react_data.pop(category)
                except KeyError:
                    return

            @discord.ui.button(label='Update/Add a role', style=discord.ButtonStyle.green, row=1)
            async def send_updaterole(self, interaction: discord.Interaction, button: discord.ui.Button):
                role_info = RoleView_add(interaction.guild)
                await interaction.response.send_message(view=role_info, ephemeral=True, delete_after=20.0)
                await role_info.wait()

                # Rip data
                role_name = role_info.role.role_name
                role_id = role_info.role.role_id
                category = role_info.role.info.category
                role_desc = role_info.role.info.role_desc
                emoji_id = role_info.emoji.emoji_id

                # Update dict
                try:
                    react_data[category]['Roles'][str(role_id)]
                except KeyError:
                    react_data[category]['Roles'][str(role_id)] = {}
                    react_data[category]['Roles'][str(role_id)]['Name'] = role_name
                    react_data[category]['Roles'][str(role_id)]['Description'] = role_desc
                    react_data[category]['Roles'][str(role_id)]['Emoji_ID'] = emoji_id

            @discord.ui.button(label='Delete a role', style=discord.ButtonStyle.red, row=1)
            async def send_deleterole(self, interaction: discord.Interaction, button: discord.ui.Button):
                role_info = RoleView_delete()
                await interaction.response.send_message(view=role_info, ephemeral=True, delete_after=20.0)
                await role_info.wait()

                # Rip data
                role_id = role_info.role.id
                category = role_info.role.info.category

                # Remove from dict
                try:
                    react_data[category]['Roles'].pop(str(role_id))
                except KeyError:
                    return

        # Send view
        view = View()
        await interaction.response.send_message(view=view, ephemeral=True)

        # Wait
        await view.wait()
        await interaction.edit_original_response(content="This view has timed out.")

        # Update Database
        try:
            async with self.bot.pool.acquire() as con:
                await con.execute("UPDATE serverdata SET react_data=$1 WHERE guild_id=$2", react_data, interaction.guild.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.edit_original_response(content="There was an error updating your data, please try again.", view=None)
        except Exception as e:
            logger.exception(e)
            await interaction.edit_original_response(content="There was an error, please try again.", view=None)
        else:
            await interaction.edit_original_response(view=None)
            await interaction.channel.send(f"Reactions updated by {interaction.user.mention}.")


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(react(bot))