"""Uses X (Twitter) API v2 to alert on new tweets from @CEN_Tweets"""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = ["Justin Panchula", "Claude"]
__version__ = "0.2.0"
__status__ = "Development"

# Standard library
import json
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo
from logging import getLogger
from pathlib import Path

# Third-party
import aiohttp
import discord
from discord.ext import commands, tasks

# Internal
from start import CENBot

log = getLogger('CENBot.twitter')

ALERT_CHANNEL_ID = int(os.getenv("TWITTER_ALERT_CHANNEL_ID"))
TWITTER_USERNAME = "CEN_Tweets"
DATA_FILE = Path(r"./cogs/data/twitter.json")
BASE_URL = "https://api.twitter.com/2/"
EMBED_COLOR = 0x1D9BF0

# Noon to 9pm ET, hourly (handles EST/EDT automatically)
_ET = ZoneInfo("America/New_York")
POLL_TIMES = [time(hour=h, tzinfo=_ET) for h in range(12, 22)]


class Twitter(commands.Cog):
    """Posts new tweets from @CEN_Tweets to a Discord channel."""

    def __init__(self, bot: CENBot) -> None:
        self.bot = bot
        self.token = os.getenv("TWITTER_TOKEN")
        self._twitter_user_id: str | None = None
        self._display_name: str | None = None
        self._last_tweet_id: str | None = None
        self._load_state()

    ### State ###

    def _load_state(self) -> None:
        if DATA_FILE.exists():
            try:
                data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                self._twitter_user_id = data.get("twitter_user_id")
                self._display_name = data.get("display_name")
                self._last_tweet_id = data.get("last_tweet_id")
            except (json.JSONDecodeError, OSError) as e:
                log.warning(f"Could not load Twitter state: {e}")

    def _save_state(self) -> None:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            DATA_FILE.write_text(
                json.dumps({
                    "twitter_user_id": self._twitter_user_id,
                    "display_name": self._display_name,
                    "last_tweet_id": self._last_tweet_id,
                }, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            log.warning(f"Could not save Twitter state: {e}")

    ### Lifecycle ###

    async def cog_load(self) -> None:
        """Resolve user ID, cache profile info, initialise tweet watermark, then start polling."""
        headers = {"Authorization": f"Bearer {self.token}"}

        async with aiohttp.ClientSession(headers=headers) as session:
            # Resolve @CEN_Tweets once; also fetches display name for embeds
            if self._twitter_user_id is None:
                async with session.get(
                    BASE_URL + f"users/by/username/{TWITTER_USERNAME}",
                    params={"user.fields": "name"},
                ) as resp:
                    if resp.status != 200:
                        log.error(f"Failed to resolve @{TWITTER_USERNAME}: HTTP {resp.status}")
                        return
                    data: dict[str, dict[str, str]] = await resp.json()
                    user = data["data"]
                    self._twitter_user_id = user["id"]
                    self._display_name = user.get("name", TWITTER_USERNAME)
                    log.info(f"Resolved @{TWITTER_USERNAME} → {self._twitter_user_id}")

            # Seed last_tweet_id to avoid re-posting on first start
            if self._last_tweet_id is None:
                async with session.get(
                    BASE_URL + f"users/{self._twitter_user_id}/tweets",
                    params={"max_results": "5"},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        tweets = data.get("data") or []
                        if tweets:
                            self._last_tweet_id = tweets[0]["id"]
                            log.info(f"Initialised last_tweet_id → {self._last_tweet_id}")
                    else:
                        log.error(f"Failed to seed last_tweet_id: HTTP {resp.status}")

        self._save_state()
        self.check_twitter.start()

    async def cog_unload(self) -> None:
        """Stop the polling task."""
        self.check_twitter.stop()

    ### Tasks ###

    @tasks.loop(time=POLL_TIMES)
    async def check_twitter(self) -> None:
        """Poll @CEN_Tweets for new tweets and post embeds to the alert channel.

        Runs hourly noon–9pm ET. Uses since_id so only genuinely new tweets are
        fetched. Posts oldest-first so the channel timeline reads naturally.
        """
        if self._twitter_user_id is None:
            log.warning("Twitter user ID not resolved; skipping check")
            return

        log.info("Checking @CEN_Tweets for new tweets...")

        params: dict[str, str] = {
            "tweet.fields": "created_at,attachments",
            "expansions": "attachments.media_keys",
            "media.fields": "url,type",
            "max_results": "5",
        }
        if self._last_tweet_id:
            params["since_id"] = self._last_tweet_id

        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(
                    BASE_URL + f"users/{self._twitter_user_id}/tweets",
                    params=params,
                ) as resp:
                    if resp.status != 200:
                        log.error(f"X API returned {resp.status}")
                        return
                    data = await resp.json()
        except aiohttp.ClientError as e:
            log.exception(e)
            return

        tweets = data.get("data") or []
        if not tweets:
            log.info("No new tweets")
            return

        # Index media by key so each tweet can look up its attachment
        media_map: dict[str, str] = {}
        for media in (data.get("includes") or {}).get("media", []):
            if media.get("type") == "photo" and media.get("url"):
                media_map[media["media_key"]] = media["url"]

        self._last_tweet_id = tweets[0]["id"]
        self._save_state()

        channel = self.bot.get_channel(ALERT_CHANNEL_ID)
        if channel is None:
            log.error(f"Alert channel {ALERT_CHANNEL_ID} not found")
            return

        # Post oldest-first
        for tweet in reversed(tweets):
            tweet_url = f"https://twitter.com/{TWITTER_USERNAME}/status/{tweet['id']}"

            embed = discord.Embed(
                description=tweet["text"],
                color=EMBED_COLOR,
                timestamp=datetime.fromisoformat(tweet["created_at"]),
            )
            embed.set_author(
                name=f"{self._display_name} (@{TWITTER_USERNAME})",
                icon_url=self.bot.user.display_avatar.url,
                url=tweet_url,
            )
            embed.set_footer(text="X")

            media_keys = (tweet.get("attachments") or {}).get("media_keys") or []
            for key in media_keys:
                if key in media_map:
                    embed.set_image(url=media_map[key])
                    break

            await channel.send(
                content=f"Hey, **{TWITTER_USERNAME}** just posted a new Tweet!",
                embed=embed,
            )

        log.info(f"Posted {len(tweets)} new tweet(s)")


async def setup(bot: CENBot) -> None:
    await bot.add_cog(Twitter(bot))
