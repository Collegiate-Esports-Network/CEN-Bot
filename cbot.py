__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Custom Bot class"""

# Python imports
import os
import asyncpg

# Discord imports
import discord
from discord.ext.commands import Bot

# Logging
import logging
logger = logging.getLogger('CENBot')

# Init intents
intents = discord.Intents.all()
intents.presences = True
intents.members = True
intents.message_content = True


# Create custom bot subclass
class cbot(Bot):
    def __init__(self) -> None:
        super().__init__(
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.playing, name='big brother'),
            description="The in-house developed CEN Bot",
            command_prefix="$$"
        )
        self.version = '2.0.0'
        self.first_time = True

        # Define the PostgreSQL connection once
        password = os.getenv("POSTGRESQL_PASS")
        self.cnx_str = str(f"postgresql://cenbot:{password}@cenbot-do-user-12316711-0.b.db.ondigitalocean.com:25060/cenbot?sslmode=require")
        self.pool = None

    async def setup_hook(self) -> None:
        # Announce connectiong
        logger.info(f"{self.user.display_name} is connecting...")
        # Create DB Connection
        self.pool = await asyncpg.create_pool(self.cnx_str)

        # Create extension lists
        found_extensions = []
        loaded_extensions = []
        failed_extensions = []

        # Scrape for extensions
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                found_extensions.append(f'cogs.{file[:-3]}')

        # Load extensions
        for extension in found_extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                failed_extensions.append(extension)
                logger.warning(e)
            else:
                loaded_extensions.append(extension)

        # Log extensions
        logger.info(f"{loaded_extensions} loaded")
        if len(failed_extensions) != 0:
            logger.warning(f"{failed_extensions} not loaded")

        # Force command sync
        await self.tree.sync()

    async def on_ready(self) -> None:
        logger.info(f"{self.user.display_name} has logged in")

        # Test first time logon
        if self.first_time is True:
            # Set to false
            self.first_time = False
            logger.info("PostgreSQL server sync started")
            try:
                for guild in self.guilds:
                    async with self.pool.acquire() as con:
                        await con.execute("INSERT INTO serverdata (guild_id) VALUES ($1) ON CONFLICT DO NOTHING", guild.id)
                        await con.execute("INSERT INTO xp (guild_id) VALUES ($1) ON CONFLICT DO NOTHING", guild.id)
                logger.info("PostgreSQL server sync completed")
            except asyncpg.PostgresError as e:
                logger.error(e)