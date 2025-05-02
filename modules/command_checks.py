__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Command Checks"""

# Modules
from modules.errors import ModuleNotEnabled

# Discord imports
from discord.ext import commands

# Logging
from logging import getLogger
log = getLogger('CENBot')


def is_enabled() -> commands.check:
    async def predicate(ctx: commands.Context) -> bool:
        try:
            async with ctx.bot.db_pool.acquire() as conn:
                record = await conn.fetchrow("SELECT * FROM cenbot.guilds WHERE guild_id=$1", ctx.guild.id)
        except Exception as e:
            log.exception(e)
            return False

        if record:
            return record[f'{ctx.command.parent.qualified_name.lower()}_enabled']
        else:
            raise ModuleNotEnabled()

    return commands.check(predicate)