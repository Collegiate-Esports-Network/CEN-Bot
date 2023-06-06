__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Custom Bot class"""

# Python imports
import os
import asyncpg
from datetime import datetime

# Discord imports
import discord
from discord.ext import tasks
from discord.ext.commands import Bot

# Logging
import logging
from asyncpg.exceptions import PostgresError
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
        self.version = '2.2.0'

        # Define the PostgreSQL connection once
        password = os.getenv('POSTGRESQL_PASS')
        self.cnx_str = str(f"postgresql://cenbot:{password}@cenbot-do-user-12316711-0.b.db.ondigitalocean.com:25060/cenbot?sslmode=require")
        self.db_pool = None

    async def setup_hook(self) -> None:
        # Announce connectiong
        logger.info(f"{self.user.display_name} is connecting...")

        # Create DB Connection
        try:
            self.db_pool = await asyncpg.create_pool(self.cnx_str)
        except:
            logger.exception("Error connecting to database")
        else:
            logger.info("DB connection established")

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

        # Start tasks
        logger.info("Starting tasks")
        self.timed_messages_send.start()

    async def on_ready(self) -> None:
        logger.info(f"{self.user.display_name} has logged in")

    # Timed messages send loop
    @tasks.loop(seconds=60)
    async def timed_messages_send(self):
        # Get current datetime
        now = datetime.now()

        # Fetch all messages that need to be sent
        try:
            async with self.db_pool.acquire() as con:
                response = await con.fetch("SELECT * FROM timedmessages WHERE time_hour=$1 AND time_minute=$2 AND (dow=$3 OR dow=0)", now.hour, now.minute, now.date().isoweekday())
        except PostgresError as e:
            logger.exception(e)
        except Exception as e:
            logger.exception(e)
        else:
            # Send all messages
            for record in response:
                channel_id = record['channel_id']
                content = record['content']

                await self.get_channel(channel_id).send(content)

    @timed_messages_send.before_loop
    async def before_loop(self):
        await self.wait_until_ready()