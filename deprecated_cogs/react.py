__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Reaction role functions"""

# Python imports
import asyncio

# Discord imports
from cbot import cbot
import discord
from discord.ext import commands
from discord import app_commands

# Typing
from typing import Optional

# Logging
import logging
from asyncpg.exceptions import PostgresError
logger = logging.getLogger('react')


class react(commands.GroupCog, name='react'):
    """These are the reaction role functions.
    """
    # Init
    def __init__(self, bot: cbot) -> None:
        self.bot = bot
        super().__init__()

    # Set reaction channel
    @app_commands.command(
        name='setchannel',
        description="Sets the reaction channel."
    )
    @commands.has_role('bot manager')
    async def react_setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("UPDATE serverdata SET react_channel=$1 WHERE guild_id=$2", channel.id, interaction.guild.id,)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error updating your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("React channel saved.", ephemeral=False)

    # Updates/Adds a category
    @app_commands.command(
        name='updatecategory',
        description="Updates/Adds a react category."
    )
    @app_commands.describe(
        cate_name="The category name.",
        cate_name_new="The new category name",
        cate_desc="The category description."
    )
    @app_commands.rename(
        cate_name='category_name',
        cate_name_new='category_name_new',
        cate_desc='category_description'
    )
    @commands.has_role('bot manager')
    async def react_updatecategory(self, interaction: discord.Interaction, cate_name: str, cate_desc: Optional[str], cate_name_new: Optional[str]) -> None:
        # Test if record already exists
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT 1 FROM reactcategory WHERE guild_id=$1 AND cate_name=$2", interaction.guild.id, cate_name)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error upserting your data, please try again.", ephemeral=True)
            return
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            return
        if len(response) == 0:
            # Insert data
            try:
                async with self.bot.db_pool.acquire() as con:
                    await con.execute("INSERT INTO reactcategory (guild_id, cate_name, cate_desc) VALUES ($1, $2, $3)", interaction.guild.id, cate_name, cate_desc)
            except PostgresError as e:
                logger.exception(e)
                await interaction.response.send_message("There was an error upserting your data, please try again.", ephemeral=True)
            except Exception as e:
                logger.exception(e)
                await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            else:
                await interaction.response.send_message(f"React category '{cate_name}' inserted.", ephemeral=False)
        else:
            # Update data
            if cate_name_new is not None:
                try:
                    async with self.bot.db_pool.acquire() as con:
                        if cate_desc is not None:
                            await con.execute("UPDATE reactcategory SET cate_desc=$1, cate_name=$4 WHERE guild_id=$2 AND cate_name=$3", cate_desc, interaction.guild.id, cate_name, cate_name_new)
                        else:
                            await con.execute("UPDATE reactcategory SET cate_name=$3 WHERE guild_id=$1 AND cate_name=$2", interaction.guild.id, cate_name, cate_name_new)
                except PostgresError as e:
                    logger.exception(e)
                    await interaction.response.send_message("There was an error upserting your data, please try again.", ephemeral=True)
                except Exception as e:
                    logger.exception(e)
                    await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"React category '{cate_name_new}' updated.", ephemeral=False)
            else:
                try:
                    async with self.bot.db_pool.acquire() as con:
                        await con.execute("UPDATE reactcategory SET cate_desc=$1 WHERE guild_id=$2 AND cate_name=$3", cate_desc, interaction.guild.id, cate_name)
                except PostgresError as e:
                    logger.exception(e)
                    await interaction.response.send_message("There was an error upserting your data, please try again.", ephemeral=True)
                except Exception as e:
                    logger.exception(e)
                    await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"React category '{cate_name}' updated.", ephemeral=False)

    # Deletes a react category
    @app_commands.command(
        name='deletecategory',
        description="Deletes a react category."
    )
    @app_commands.describe(
        cate_name="The category name. Case sensitive.",
    )
    @app_commands.rename(
        cate_name='category_name',
    )
    @commands.has_role('bot manager')
    async def react_deletecategory(self, interaction: discord.Interaction, cate_name: str) -> None:
        # Fetch react channel
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT react_channel FROM serverdata WHERE guild_id=$1", interaction.guild.id)
                channel = response[0]['react_channel']
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again.", ephemeral=True)
            return
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            return

        # Fetch embed
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT message_id FROM reactcategory WHERE cate_name=$1 AND guild_id=$2", cate_name, interaction.guild.id)
                message_id = response[0]['message_id']
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error fetching your data, please try again.", ephemeral=True)
            return
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
            return

        # Delete category
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("DELETE FROM reactcategory WHERE cate_name=$1 AND guild_id=$2", cate_name, interaction.guild.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error deleting your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message(f"React category '{cate_name}' deleted.", ephemeral=False)

        # Delete embed
        message = await self.bot.get_channel(channel).fetch_message(message_id)
        await message.delete()

    # Updates/Adds a react role
    @app_commands.command(
        name='updatereaction',
        description="Updates/Adds a reaction role."
    )
    @app_commands.describe(
        role="The role mention.",
        cate_name="The category this role is under. Case sensitive."
    )
    @app_commands.rename(
        cate_name='category_name'
    )
    @commands.has_role('bot manager')
    async def react_updatereaction(self, interaction: discord.Interaction, role: discord.Role, cate_name: str) -> None:
        # Defer response
        await interaction.response.defer(ephemeral=False)

        # Get category id from name
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT category_id FROM reactcategory WHERE guild_id=$1 AND cate_name=$2", interaction.guild.id, cate_name)
            category_id = response[0]['category_id']
        except PostgresError as e:
            logger.exception(e)
            await interaction.followup.send("There was an error retrieving your data, please try again.", ephemeral=True)
            return
        except IndexError:
            await interaction.followup.send(f"'{cate_name}' is not a valid category, please try again.", ephemeral=True)
            return
        except Exception as e:
            logger.exception(e)
            await interaction.followup.send("There was an error, please try again.", ephemeral=True)
            return

        wmessage = await interaction.followup.send("React to this message with the emoji you'd like to use. (15s timer)", ephemeral=False)
        await asyncio.sleep(15)
        try:
            # Handling different emoji types
            message = await wmessage.fetch()
            emoji = message.reactions[0].emoji
            if type(emoji) is not str:
                emoji = str(emoji.id)
            await message.delete()
        except IndexError:
            await interaction.followup.send(f"There was an error getting the emoji for react role {role.name}, please try again.", ephemeral=True)
            return

        # Valid <25 existing reactions
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT * FROM reactdata WHERE category_id=$1", category_id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.followup.send("There was an error upserting your data, please try again.", ephemeral=True)
            return
        except Exception as e:
            logger.exception(e)
            await interaction.followup.send("There was an error, please try again.", ephemeral=True)
            return
        if len(response) >= 25:
            await interaction.followup.send("You have reached the 25 button maximum for this category. Please consider deleting a reaction or creating a new category")
            return

        # Upsert data
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT * FROM reactdata WHERE role_id=$1 AND category_id=$2", role.id, category_id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.followup.send("There was an error upserting your data, please try again.", ephemeral=True)
            return
        except Exception as e:
            logger.exception(e)
            await interaction.followup.send("There was an error, please try again.", ephemeral=True)
            return
        if len(response) == 0:
            # Insert data
            try:
                async with self.bot.db_pool.acquire() as con:
                    await con.execute("INSERT INTO reactdata (role_id, category_id, role_emoji) VALUES ($1, $2, $3)", role.id, category_id, emoji)
            except PostgresError as e:
                logger.exception(e)
                await interaction.followup.send("There was an error upserting your data, please try again.", ephemeral=True)
            except Exception as e:
                logger.exception(e)
                await interaction.followup.send("There was an error, please try again.", ephemeral=True)
            else:
                await interaction.followup.send(f"Reaction for '{role.name}' added.", ephemeral=False)
        else:
            # Update data
            try:
                async with self.bot.db_pool.acquire() as con:
                    await con.execute("UPDATE reactdata SET category_id=$1, role_emoji=$2 WHERE role_id=$3", category_id, emoji, role.id)
            except PostgresError as e:
                logger.exception(e)
                await interaction.followup.send("There was an error upserting your data, please try again.", ephemeral=True)
            except Exception as e:
                logger.exception(e)
                await interaction.followup.send("There was an error, please try again.", ephemeral=True)
            else:
                await interaction.followup.send(f"Reaction for '{role.name}' updated.", ephemeral=False)

    # Deletes a reaction role
    @app_commands.command(
        name='deletereaction',
        description="Deletes a reaction role."
    )
    @app_commands.describe(
        role="The role mention."
    )
    @commands.has_role('bot manager')
    async def react_deletereaction(self, interaction: discord.Interaction, role: discord.Role) -> None:
        # Delete reaction
        try:
            async with self.bot.db_pool.acquire() as con:
                await con.execute("DELETE FROM reactdata WHERE role_id=$1", role.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error deleting your data, please try again.", ephemeral=True)
        except Exception as e:
            logger.exception(e)
            await interaction.response.send_message("There was an error, please try again.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Reaction for '{role.name}' deleted.", ephemeral=False)

    # Builds and sends reaction embeds
    @app_commands.command(
        name='update',
        description="Updates the react embeds and sends new ones for new categories."
    )
    @commands.has_role('bot manager')
    async def react_update(self, interaction: discord.Interaction) -> None:
        # Defer response
        await interaction.response.defer(ephemeral=False)

        # Get channel
        try:
            async with self.bot.db_pool.acquire() as con:
                response = await con.fetch("SELECT react_channel FROM serverdata WHERE guild_id=$1", interaction.guild.id)
            channel = response[0]['react_channel']
        except PostgresError as e:
            logger.exception(e)
            await interaction.followup.send("There was an error fetching your data, please try again.", ephemeral=True)
            return
        except AttributeError:
            await interaction.followup.send("There is no react channel set.", ephemeral=True)
            return

        # Get all categories
        try:
            async with self.bot.db_pool.acquire() as con:
                categories = await con.fetch("SELECT * FROM reactcategory WHERE guild_id=$1 ORDER BY cate_name ASC", interaction.guild.id)
        except PostgresError as e:
            logger.exception(e)
            await interaction.followup.send("There was an error fetching your data, please try again.", ephemeral=True)
            return
        except AttributeError:
            await interaction.followup.send("There was an error, please try again.", ephemeral=True)
            return

        # Create default button
        class ReactButton(discord.ui.Button):
            def __init__(self, role_id, role_name, role_emoji):
                super().__init__(style=discord.ButtonStyle.blurple, label=role_name, emoji=role_emoji, custom_id=str(role_id))
                self.role = interaction.guild.get_role(role_id)

            async def callback(self, interaction: discord.Interaction):
                # Get member who clicked
                member = interaction.user

                # Check if member already has role
                if self.role not in member.roles:
                    # Add role to member
                    try:
                        await member.add_roles(self.role)
                    except discord.Forbidden and discord.HTTPException:
                        await interaction.response.send_message(f"There was an error giving you the ``{self.role.name}`` role, please try again.", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"You have been given the ``{self.role.name}`` role.", ephemeral=True)
                else:
                    # Remove role from member
                    try:
                        await member.remove_roles(self.role)
                    except discord.Forbidden and discord.HTTPException:
                        await interaction.response.send_message(f"There was an error removing the ``{self.role.name}`` role from you, please try again.", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"The ``{self.role.name}`` role has been removed from you.", ephemeral=True)

        # Build message
        for category in categories:
            # Rip data
            cate_id = category['category_id']
            cate_name = category['cate_name']
            cate_desc = category['cate_desc']
            message_id = category['message_id']

            # Get all roles
            try:
                async with self.bot.db_pool.acquire() as con:
                    roles = await con.fetch("SELECT * FROM reactdata WHERE category_id=$1", cate_id)
            except PostgresError as e:
                logger.exception(e)
                await interaction.followup.send("There was an error fetching your data, please try again.", ephemeral=True)
            except AttributeError:
                await interaction.followup.send("There was an error, please try again.", ephemeral=True)

            # Create Role view
            class Roles(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)
            RoleView = Roles()

            # Add roles
            for role in roles:
                # Rip data
                role_id = role['role_id']
                role_emoji = role['role_emoji']

                # Get emoji from id
                try:
                    emoji = self.bot.get_emoji(int(role_emoji))
                except ValueError:  # Unicode switch
                    emoji = role_emoji

                # Get role name from id
                role_name = interaction.guild.get_role(role_id).name

                # Create role button
                role_button = ReactButton(role_id, role_name, emoji)

                # Add to view
                RoleView.add_item(role_button)

            # Check for previous message
            if message_id is not None:
                # Get previous message
                try:
                    message = await self.bot.get_channel(channel).fetch_message(message_id)
                except discord.errors.NotFound:
                    await interaction.followup.send("There was an error updating reactions, please try again.", ephemeral=True)
                else:
                    # Edit message
                    await message.edit(content=f"**{cate_name}**\n{cate_desc}", view=RoleView)

                    # Add view persistance
                    self.bot.add_view(view=RoleView, message_id=message.id)
            else:
                # Send message
                message = await self.bot.get_channel(channel).send(f"**{cate_name}**\n{cate_desc}", view=RoleView)

                # Add view persistance
                self.bot.add_view(view=RoleView, message_id=message.id)

                # Save message id
                try:
                    async with self.bot.db_pool.acquire() as con:
                        await con.execute("UPDATE reactcategory SET message_id=$1 WHERE category_id=$2", message.id, cate_id)
                except PostgresError as e:
                    logger.exception(e)
                    await interaction.followup.send("There was an error saving your data, please try again.", ephemeral=True)
                except AttributeError:
                    await interaction.followup.send("There was an error, please try again.", ephemeral=True)

        await interaction.followup.send("Reactions updated", ephemeral=False)


# Add to bot
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(react(bot))