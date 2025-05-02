__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """App Command Checks"""

# Modules
from modules.errors import ModuleNotEnabled

# Discord imports
import discord
from discord import app_commands

# Logging
from logging import getLogger
log = getLogger('CENBot')


def is_app_enabled() -> app_commands.check:
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            async with interaction.client.db_pool.acquire() as conn:
                record = await conn.fetchrow("SELECT * FROM cenbot.guilds WHERE guild_id=$1", interaction.guild.id)
        except Exception as e:
            log.exception(e)
            return False

        if record:
            return record[f'{interaction.command.parent.qualified_name.lower()}_enabled']
        else:
            raise ModuleNotEnabled()

    return app_commands.check(predicate)